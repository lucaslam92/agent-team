"""
Command Layer — handles built-in local commands that do NOT go to codex.

Built-in commands:
  /help           — show command list
  /status         — show bridge status (uptime, active sessions, codex version)
  /pwd            — show current working directory for this conversation
  /cd <path>      — change working directory for this conversation
  /clear          — reset the working directory to default and clear session state

Commands are matched case-insensitively at the start of the message content.
Returns None if the message is not a command (caller should forward to codex).
"""
from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_START_TIME = time.time()

HELP_TEXT = """\
QQ Codex Bridge — available commands:

  /help           Show this message
  /status         Bridge status and codex version
  /pwd            Current working directory for this chat
  /cd <path>      Change working directory for this chat
  /clear          Reset working directory to default

Anything else is forwarded directly to codex CLI.
Attach an image to pass it as a file argument to codex.
""".strip()


def handle_command(
    text: str,
    *,
    session_workdir: str,
    default_workdir: str,
) -> Optional[tuple[str, str]]:
    """
    Try to handle `text` as a built-in command.

    Returns
    -------
    (reply_text, new_workdir) if handled, else None.

    The caller is responsible for persisting new_workdir back to the session.
    """
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None

    # Split into command + args (safe shell splitting)
    try:
        parts = shlex.split(stripped)
    except ValueError:
        parts = stripped.split()

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == "/help":
        return HELP_TEXT, session_workdir

    if cmd == "/status":
        return _status(session_workdir), session_workdir

    if cmd == "/pwd":
        return f"Current directory: {session_workdir}", session_workdir

    if cmd == "/cd":
        return _cd(args, session_workdir=session_workdir, default_workdir=default_workdir)

    if cmd == "/clear":
        return f"Session reset. Working directory: {default_workdir}", default_workdir

    # Unknown slash command — do NOT forward to codex; tell user
    return f"Unknown command: {cmd}\nType /help for available commands.", session_workdir


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _status(session_workdir: str) -> str:
    uptime_s = int(time.time() - _START_TIME)
    h, rem = divmod(uptime_s, 3600)
    m, s = divmod(rem, 60)
    uptime_str = f"{h}h {m}m {s}s"

    codex_path = shutil.which("codex") or "(not found in PATH)"
    codex_version = _get_codex_version()

    return (
        f"Bridge status\n"
        f"  Uptime    : {uptime_str}\n"
        f"  Codex     : {codex_path}\n"
        f"  Version   : {codex_version}\n"
        f"  Workdir   : {session_workdir}"
    )


def _get_codex_version() -> str:
    try:
        result = subprocess.run(
            ["codex", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return (result.stdout or result.stderr).strip() or "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "unavailable"


def _cd(
    args: list[str],
    *,
    session_workdir: str,
    default_workdir: str,
) -> tuple[str, str]:
    if not args:
        # /cd with no args → go home
        new_dir = default_workdir
    else:
        target = args[0]
        # Support ~
        target = os.path.expanduser(target)
        if not os.path.isabs(target):
            target = os.path.join(session_workdir, target)
        target = os.path.normpath(target)
        new_dir = target

    if not os.path.isdir(new_dir):
        return f"Directory not found: {new_dir}", session_workdir

    return f"Changed directory to: {new_dir}", new_dir
