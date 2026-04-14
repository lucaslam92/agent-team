"""
QQ Codex Bridge — main entry point.

Connects to QQ's WebSocket gateway and wires together all layers.

Flow per incoming message:
  QQ WS event → Message Router → Command Layer?
      → (if not command) download attachments → Codex Bridge
      → Reply Sender → QQ API

Usage:
  python -m qq_codex_bridge.main
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from typing import Optional

from qq_codex_bridge.bridge.codex import download_attachment
from qq_codex_bridge.bridge.context import SessionStore, make_session_id
from qq_codex_bridge.bridge import executor
from qq_codex_bridge.config import AppConfig, load_config
from qq_codex_bridge.gateway.models import IncomingMessage
from qq_codex_bridge.gateway.ws_client import BotGatewayClient
from qq_codex_bridge.reply.sender import ReplySender
from qq_codex_bridge.router.command import handle_command
from qq_codex_bridge.router.message import normalize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)


async def dispatch(
    payload: dict,
    config: AppConfig,
    store: SessionStore,
    sender: ReplySender,
) -> None:
    """
    Top-level message handler for each QQ event.

    1. Normalize raw QQ event → IncomingMessage
    2. Resolve session context (workdir)
    3. Check for local /command
    4. Download any image attachments
    5. Run codex exec
    6. Send reply
    """
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

    # Step 1: handle built-in /commands
    if msg.content.startswith("/"):
        result = handle_command(
            msg.content,
            session_workdir=ctx.workdir,
            session_model=ctx.model,
            default_workdir=config.codex.default_workdir,
        )
        if result is not None:
            store.update_workdir(session_id, result.new_workdir)
            if result.new_model is not None:
                store.update_model(session_id, result.new_model)
            await sender.send(result.reply, source=msg)
            return

    # Step 2: download image attachments (skip video for now)
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

    image_paths += store.pop_pending_files(session_id)

    # Step 3: run codex exec
    if not msg.content and not image_paths:
        await sender.send("(empty message — nothing to do)", source=msg)
        return

    result = await executor.run(
        prompt=msg.content,
        model=ctx.model,
        workdir=ctx.workdir,
        codex_binary=config.codex.binary,
        image_paths=image_paths or None,
        timeout=config.gateway.exec_timeout,
    )

    # Step 4: compose and send reply
    if result.timed_out:
        reply = (
            f"[Timeout] codex exec exceeded {config.gateway.exec_timeout}s.\n\n"
            f"Partial output:\n{result.combined}"
        )
    elif not result.success:
        reply = (
            f"[Exit {result.returncode}]\n{result.combined}"
            if result.combined
            else f"codex exited with code {result.returncode}"
        )
    else:
        reply = result.combined or "(codex produced no output)"

    await sender.send(reply, source=msg)


async def main() -> None:
    config = load_config()

    store = SessionStore(default_workdir=config.codex.default_workdir)
    sender = ReplySender(
        app_id=config.bot.app_id,
        token=config.bot.token,
        sandbox=config.bot.sandbox,
        chunk_size=config.codex.reply_chunk_size,
        max_retries=config.codex.reply_max_retries,
    )

    async def _dispatch(payload: dict) -> None:
        await dispatch(payload, config, store, sender)

    client = BotGatewayClient(
        app_id=config.bot.app_id,
        token=config.bot.token,
        sandbox=config.bot.sandbox,
        dispatch=_dispatch,
    )

    log.info("QQ Codex Bridge starting (WebSocket mode)...")
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
