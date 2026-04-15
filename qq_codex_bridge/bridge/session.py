"""
Persistent CLI session via tmux.

每个 QQ 会话对应一个 tmux window，CLI（codex / claude）在其中常驻运行。
收到消息时：
  1. tmux send-keys 把文本发进去（等同于在终端手动输入）
  2. 轮询 capture-pane 直到内容连续 N 次不变 → 本轮回复完毕
  3. 提取本次新增内容返回给用户

tmux 能正确渲染 ncurses / TUI 输出，capture-pane 拿到的是干净的可见文本。

Default model
-------------
优先使用有 API Key 的那个：
  OPENAI_API_KEY    → codex
  ANTHROPIC_API_KEY → claude
  两者都没有        → codex（运行时会因无 key 报错）
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import threading
import time
from typing import Optional

log = logging.getLogger(__name__)

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[mGKHFJA-Z]')

# How long to wait after tmux new-session before reading the startup screen
_STARTUP_WAIT = 6.0


def _clean(text: str) -> str:
    return _ANSI_RE.sub('', text)


def detect_default_model() -> str:
    if os.environ.get('OPENAI_API_KEY'):
        return 'codex'
    if os.environ.get('ANTHROPIC_API_KEY'):
        return 'claude'
    return 'codex'


class TmuxSession:
    """
    One tmux window running an interactive CLI (codex or claude).

    Usage:
        sess = TmuxSession("grp_abc", model="claude", workdir="/home/user")
        reply = sess.send_recv("帮我写一个 hello world")
    """

    def __init__(self, name: str, model: str, workdir: str) -> None:
        # tmux session name must be alphanumeric + underscore
        self.name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        self.model = model
        self.workdir = workdir
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def is_alive(self) -> bool:
        r = subprocess.run(
            ['tmux', 'has-session', '-t', self.name],
            capture_output=True,
        )
        return r.returncode == 0

    def send_recv(
        self,
        text: str,
        *,
        poll_interval: float = 0.5,
        stable_rounds: int = 6,   # N consecutive unchanged captures → done
        timeout: float = 120.0,
    ) -> str:
        """Send text, wait for response to stabilise, return new output."""
        with self._lock:
            if not self.is_alive():
                self._start()

            # Snapshot screen before sending
            before = self._capture()
            log.debug("[%s] Screen before send (%d chars):\n%s",
                      self.name, len(before), before[:400])

            # Type the message
            self._send_keys(text)
            log.info("[%s] >>> sent: %r", self.name, text[:120])

            # Poll until screen stable
            prev = before
            stable = 0
            elapsed = 0.0
            after = before

            while elapsed < timeout:
                time.sleep(poll_interval)
                elapsed += poll_interval
                cur = self._capture()

                if cur == prev:
                    stable += 1
                    log.debug("[%s] poll %.1fs — stable %d/%d",
                              self.name, elapsed, stable, stable_rounds)
                    if stable >= stable_rounds:
                        after = cur
                        log.info("[%s] Response stable after %.1fs", self.name, elapsed)
                        break
                else:
                    if stable > 0:
                        log.debug("[%s] poll %.1fs — screen changed (was stable %d)",
                                  self.name, elapsed, stable)
                    else:
                        log.debug("[%s] poll %.1fs — screen changed", self.name, elapsed)
                    stable = 0
                    prev = cur
            else:
                log.warning("[%s] Timed out after %.0fs — returning whatever is on screen",
                            self.name, timeout)
                after = self._capture()

            result = _extract_new(before, after)
            log.info("[%s] <<< reply (%d chars): %r", self.name, len(result), result[:300])
            return result

    def close(self) -> None:
        if self.is_alive():
            log.info("[%s] Closing tmux session", self.name)
            subprocess.run(
                ['tmux', 'kill-session', '-t', self.name],
                capture_output=True,
            )

    def switch(self, *, model: Optional[str] = None, workdir: Optional[str] = None) -> None:
        """Kill and restart with new model / workdir."""
        self.close()
        if model:
            self.model = model
        if workdir:
            self.workdir = workdir
        # Will re-spawn on next send_recv()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _start(self) -> None:
        log.info("[%s] Launching tmux session: %s in %s",
                 self.name, self.model, self.workdir)
        result = subprocess.run(
            [
                'tmux', 'new-session', '-d',
                '-s', self.name,
                '-x', '220', '-y', '50',
                '-c', self.workdir,
                self.model,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.error("[%s] tmux new-session failed: %s", self.name, result.stderr.strip())
            raise RuntimeError(f"tmux new-session failed: {result.stderr.strip()}")

        log.info("[%s] tmux session created — waiting %.1fs for CLI startup...",
                 self.name, _STARTUP_WAIT)
        time.sleep(_STARTUP_WAIT)

        # Verify the CLI is actually running and log what's on screen
        screen = self._capture()
        if screen.strip():
            log.info("[%s] CLI startup screen:\n%s", self.name, screen[:600])
        else:
            log.warning("[%s] CLI startup screen is empty — may not have started correctly",
                        self.name)

    def _send_keys(self, text: str) -> None:
        subprocess.run(
            ['tmux', 'send-keys', '-t', self.name, text, 'Enter'],
            check=True,
        )

    def _capture(self) -> str:
        r = subprocess.run(
            ['tmux', 'capture-pane', '-t', self.name, '-p'],
            capture_output=True, text=True,
        )
        return r.stdout


def _extract_new(before: str, after: str) -> str:
    """
    Return lines that appeared in `after` but not in `before`.
    Falls back to the full `after` if diff is empty.
    """
    before_lines = set(before.splitlines())
    new_lines = [l for l in after.splitlines() if l not in before_lines]
    result = '\n'.join(new_lines).strip()
    return result or after.strip()


# ---------------------------------------------------------------------------
# Session manager
# ---------------------------------------------------------------------------

class SessionManager:
    """Thread-safe store of TmuxSession objects keyed by QQ session ID."""

    def __init__(self, default_workdir: str) -> None:
        self._default_workdir = default_workdir
        self._sessions: dict[str, TmuxSession] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str) -> TmuxSession:
        with self._lock:
            if session_id not in self._sessions:
                model = detect_default_model()
                self._sessions[session_id] = TmuxSession(
                    name=session_id,
                    model=model,
                    workdir=self._default_workdir,
                )
                log.info("Created session slot %s (model=%s)", session_id, model)
            return self._sessions[session_id]

    def remove(self, session_id: str) -> None:
        with self._lock:
            sess = self._sessions.pop(session_id, None)
        if sess:
            sess.close()
