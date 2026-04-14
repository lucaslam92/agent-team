"""
Command Layer — handles built-in local commands that do NOT go to the model CLI.

Built-in commands:
  /help                 — show command list
  /status               — show bridge status (uptime, current model, versions)
  /pwd                  — show current working directory for this conversation
  /cd <path>            — change working directory for this conversation
  /clear                — reset the working directory to default
  /model codex|claude   — switch active CLI backend for this session

Commands are matched case-insensitively.
Returns None if the message is not a command (caller forwards to active model CLI).
"""
from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

from qq_codex_bridge.bridge.context import ModelName, DEFAULT_MODEL

log = logging.getLogger(__name__)

_START_TIME = time.time()
SUPPORTED_MODELS: tuple[ModelName, ...] = ("codex", "claude")

HELP_TEXT = """\
QQ Codex Bridge — available commands:

  /help                 Show this message
  /status               Bridge status (uptime, active model, CLI versions)
  /pwd                  Current working directory for this chat
  /cd <path>            Change working directory for this chat
  /clear                Reset working directory to default
  /model codex|claude   Switch CLI backend for this session

Anything else is forwarded to the active CLI (codex or claude).
Attach an image to pass it as a file argument to the CLI.
""".strip()


@dataclass
class CommandResult:
    reply: str
    new_workdir: str
    new_model: Optional[ModelName] = None   # None = no change


def handle_command(
    text: str,
    *,
    session_workdir: str,
    session_model: ModelName,
    default_workdir: str,
) -> Optional[CommandResult]:
    """
    Try to handle `text` as a built-in command.

    Returns CommandResult if handled, else None (caller forwards to model CLI).
    """
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None

    try:
        parts = shlex.split(stripped)
    except ValueError:
        parts = stripped.split()

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == "/help":
        return CommandResult(reply=HELP_TEXT, new_workdir=session_workdir)

    if cmd == "/status":
        return CommandResult(reply=_status(session_workdir, session_model), new_workdir=session_workdir)

    if cmd == "/pwd":
        return CommandResult(
            reply=f"Current directory: {session_workdir}",
            new_workdir=session_workdir,
        )

    if cmd == "/cd":
        reply, new_wd = _cd(args, session_workdir=session_workdir, default_workdir=default_workdir)
        return CommandResult(reply=reply, new_workdir=new_wd)

    if cmd == "/clear":
        return CommandResult(
            reply=f"Session reset. Working directory: {default_workdir}",
            new_workdir=default_workdir,
        )

    if cmd == "/model":
        return _switch_model(args, current_model=session_model, session_workdir=session_workdir)

    # Unknown slash command
    return CommandResult(
        reply=f"Unknown command: {cmd}\nType /help for available commands.",
        new_workdir=session_workdir,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _status(session_workdir: str, session_model: ModelName) -> str:
    uptime_s = int(time.time() - _START_TIME)
    h, rem = divmod(uptime_s, 3600)
    m, s = divmod(rem, 60)

    lines = [
        "Bridge status",
        f"  Uptime   : {h}h {m}m {s}s",
        f"  Model    : {session_model}",
        f"  Workdir  : {session_workdir}",
    ]
    for name in SUPPORTED_MODELS:
        path = shutil.which(name) or "(not found)"
        ver = _get_version(name)
        lines.append(f"  {name:<8} : {path}  [{ver}]")

    return "\n".join(lines)


def _get_version(binary: str) -> str:
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return (result.stdout or result.stderr).strip().splitlines()[0] or "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "unavailable"


def _cd(
    args: list[str],
    *,
    session_workdir: str,
    default_workdir: str,
) -> tuple[str, str]:
    if not args:
        new_dir = default_workdir
    else:
        target = os.path.expanduser(args[0])
        if not os.path.isabs(target):
            target = os.path.join(session_workdir, target)
        new_dir = os.path.normpath(target)

    if not os.path.isdir(new_dir):
        return f"Directory not found: {new_dir}", session_workdir

    return f"Changed directory to: {new_dir}", new_dir


def _switch_model(
    args: list[str],
    *,
    current_model: ModelName,
    session_workdir: str,
) -> CommandResult:
    if not args:
        options = " | ".join(SUPPORTED_MODELS)
        return CommandResult(
            reply=f"Usage: /model {options}\nCurrent model: {current_model}",
            new_workdir=session_workdir,
        )

    target = args[0].lower()
    if target not in SUPPORTED_MODELS:
        options = " | ".join(SUPPORTED_MODELS)
        return CommandResult(
            reply=f"Unknown model: {target!r}\nAvailable: {options}",
            new_workdir=session_workdir,
        )

    if target == current_model:
        return CommandResult(
            reply=f"Already using {current_model}. No change.",
            new_workdir=session_workdir,
        )

    # Switch: exit current, enter new
    reply = f"Exiting {current_model} → entering {target}."
    return CommandResult(
        reply=reply,
        new_workdir=session_workdir,
        new_model=target,  # type: ignore[arg-type]
    )
