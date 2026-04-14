"""
Unified executor — dispatches to the correct CLI backend based on session model.

Supported backends
------------------
codex  →  codex exec --cwd <workdir> [--image <path>...] -- <prompt>
claude →  claude -p <prompt> [--image <path>...]
              (runs in <workdir> via subprocess cwd parameter)

Both calls are one-shot, non-interactive, with stdout+stderr captured.
ANSI escape codes are stripped from all output before returning.
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
from pathlib import Path
from typing import List, Optional

from qq_codex_bridge.bridge.codex import ExecResult, _strip_ansi
from qq_codex_bridge.bridge.context import ModelName

log = logging.getLogger(__name__)


async def run(
    *,
    prompt: str,
    model: ModelName,
    workdir: str,
    codex_binary: str = "codex",
    claude_binary: str = "claude",
    image_paths: Optional[List[str]] = None,
    timeout: int = 120,
) -> ExecResult:
    """
    Execute the prompt using the specified model CLI.

    Parameters
    ----------
    prompt:        User instruction text.
    model:         "codex" or "claude".
    workdir:       Working directory for the subprocess.
    codex_binary:  Path/name of the codex executable.
    claude_binary: Path/name of the claude executable.
    image_paths:   Local image file paths to pass to the CLI.
    timeout:       Seconds before force-kill.
    """
    if model == "codex":
        return await _run_codex(
            prompt=prompt,
            workdir=workdir,
            binary=codex_binary,
            image_paths=image_paths,
            timeout=timeout,
        )
    elif model == "claude":
        return await _run_claude(
            prompt=prompt,
            workdir=workdir,
            binary=claude_binary,
            image_paths=image_paths,
            timeout=timeout,
        )
    else:
        return ExecResult(
            stdout="",
            stderr=f"Unknown model: {model!r}",
            returncode=1,
        )


# ---------------------------------------------------------------------------
# Backend: codex
# ---------------------------------------------------------------------------

async def _run_codex(
    *,
    prompt: str,
    workdir: str,
    binary: str,
    image_paths: Optional[List[str]],
    timeout: int,
) -> ExecResult:
    bin_path = shutil.which(binary)
    if bin_path is None:
        return ExecResult(
            stdout="",
            stderr=f"codex not found: '{binary}'. Install: npm install -g @openai/codex",
            returncode=127,
        )

    cmd: List[str] = [bin_path, "exec", "--cwd", workdir]
    for img in (image_paths or []):
        if Path(img).exists():
            cmd += ["--image", img]
        else:
            log.warning("Image not found, skipping: %s", img)
    cmd += ["--", prompt]

    log.info("[codex] %s", " ".join(cmd))
    return await _exec(cmd, workdir=workdir, timeout=timeout, label="codex")


# ---------------------------------------------------------------------------
# Backend: claude (Claude Code CLI)
# ---------------------------------------------------------------------------

async def _run_claude(
    *,
    prompt: str,
    workdir: str,
    binary: str,
    image_paths: Optional[List[str]],
    timeout: int,
) -> ExecResult:
    bin_path = shutil.which(binary)
    if bin_path is None:
        return ExecResult(
            stdout="",
            stderr=f"claude not found: '{binary}'. Install: npm install -g @anthropic-ai/claude-code",
            returncode=127,
        )

    # Claude Code CLI non-interactive mode: claude -p "<prompt>"
    # Images are passed via --image flags (same convention as codex)
    cmd: List[str] = [bin_path, "-p", prompt]
    for img in (image_paths or []):
        if Path(img).exists():
            cmd += ["--image", img]
        else:
            log.warning("Image not found, skipping: %s", img)

    log.info("[claude] cwd=%s prompt=%r", workdir, prompt[:80])
    # Claude CLI respects cwd from the subprocess environment
    return await _exec(cmd, workdir=workdir, timeout=timeout, label="claude")


# ---------------------------------------------------------------------------
# Shared subprocess runner
# ---------------------------------------------------------------------------

async def _exec(
    cmd: List[str],
    *,
    workdir: str,
    timeout: int,
    label: str,
) -> ExecResult:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workdir,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            timed_out = False
        except asyncio.TimeoutError:
            log.warning("[%s] timed out after %ds — killing", label, timeout)
            proc.kill()
            stdout_bytes, stderr_bytes = await proc.communicate()
            timed_out = True

        return ExecResult(
            stdout=_strip_ansi(stdout_bytes.decode("utf-8", errors="replace")),
            stderr=_strip_ansi(stderr_bytes.decode("utf-8", errors="replace")),
            returncode=proc.returncode or 0,
            timed_out=timed_out,
        )

    except Exception as exc:
        log.exception("[%s] unexpected error", label)
        return ExecResult(stdout="", stderr=f"Bridge error: {exc}", returncode=1)
