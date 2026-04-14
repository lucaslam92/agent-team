"""
QQ Codex Bridge — main entry point.

Wires together all layers and starts the FastAPI server.

Flow per incoming message:
  QQ webhook → Event Gateway → Message Router → Command Layer?
      → (if not command) download attachments → Codex Bridge
      → Reply Sender → QQ API

Usage:
  python -m qq_codex_bridge.main
  # or with uvicorn directly:
  uvicorn qq_codex_bridge.main:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import tempfile
from typing import Optional

import uvicorn

from qq_codex_bridge.bridge.codex import download_attachment, exec_codex
from qq_codex_bridge.bridge.context import SessionStore, make_session_id
from qq_codex_bridge.config import AppConfig, load_config
from qq_codex_bridge.gateway.app import create_app
from qq_codex_bridge.gateway.models import IncomingMessage, MessageType
from qq_codex_bridge.reply.sender import ReplySender
from qq_codex_bridge.router.command import handle_command
from qq_codex_bridge.router.message import normalize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)


def _build_globals(config: AppConfig):
    """Construct shared singletons once at startup."""
    store = SessionStore(default_workdir=config.codex.default_workdir)
    sender = ReplySender(
        app_id=config.bot.app_id,
        token=config.bot.token,
        sandbox=config.bot.sandbox,
        chunk_size=config.codex.reply_chunk_size,
        max_retries=config.codex.reply_max_retries,
    )
    return store, sender


# ---------------------------------------------------------------------------
# Dispatch coroutine — called by the gateway as a background task
# ---------------------------------------------------------------------------

async def dispatch(payload: dict, config: AppConfig) -> None:
    """
    Top-level message handler.

    1. Normalize raw QQ event → IncomingMessage
    2. Resolve session context (workdir)
    3. Check for local /command
    4. Download any image attachments
    5. Run codex exec
    6. Send reply
    """
    # Singletons are module-level (set once by build_app)
    store: SessionStore = _store
    sender: ReplySender = _sender

    # Step 1: normalize
    msg: Optional[IncomingMessage] = normalize(payload)
    if msg is None:
        return

    log.info(
        "Message from %s [%s]: %r",
        msg.author_name,
        msg.event_type.value,
        msg.content[:80],
    )

    session_id = make_session_id(msg.group_openid, msg.channel_id, msg.author_id)
    ctx = store.get(session_id)

    # Step 2: handle built-in commands
    if msg.content.startswith("/"):
        result = handle_command(
            msg.content,
            session_workdir=ctx.workdir,
            default_workdir=config.codex.default_workdir,
        )
        if result is not None:
            reply_text, new_workdir = result
            store.update_workdir(session_id, new_workdir)
            await sender.send(reply_text, source=msg)
            return

    # Step 3: download image attachments (skip video for now)
    image_paths: list[str] = []
    if msg.attachments:
        tmp_dir = tempfile.mkdtemp(prefix="qq_attach_")
        for att in msg.attachments:
            if att.content_type.startswith("image/"):
                path = await download_attachment(att.url, tmp_dir)
                if path:
                    image_paths.append(path)
            elif att.content_type.startswith("video/"):
                log.info("Video attachment — skipping (not yet supported): %s", att.url)

    # Also include any files pending from a previous message
    image_paths += store.pop_pending_files(session_id)

    # Step 4: run codex exec
    if not msg.content and not image_paths:
        await sender.send("(empty message — nothing to do)", source=msg)
        return

    result = await exec_codex(
        prompt=msg.content,
        workdir=ctx.workdir,
        binary=config.codex.binary,
        image_paths=image_paths or None,
        timeout=config.gateway.exec_timeout,
    )

    # Step 5: compose and send reply
    if result.timed_out:
        reply = f"[Timeout] codex exec exceeded {config.gateway.exec_timeout}s.\n\nPartial output:\n{result.combined}"
    elif not result.success:
        reply = f"[Exit {result.returncode}]\n{result.combined}" if result.combined else f"codex exited with code {result.returncode}"
    else:
        reply = result.combined or "(codex produced no output)"

    await sender.send(reply, source=msg)


# ---------------------------------------------------------------------------
# App factory (module-level singletons)
# ---------------------------------------------------------------------------

_store: SessionStore
_sender: ReplySender


def build_app(config: Optional[AppConfig] = None):
    global _store, _sender
    cfg = config or load_config()
    _store, _sender = _build_globals(cfg)
    return create_app(cfg, dispatch)


# Module-level app for uvicorn
config = load_config()
app = build_app(config)


if __name__ == "__main__":
    uvicorn.run(
        "qq_codex_bridge.main:app",
        host=config.gateway.host,
        port=config.gateway.port,
        log_level="info",
        access_log=True,
    )
