"""
QQ Codex Bridge — main entry point.

Flow:
  QQ WS event → normalize → /command? → handle locally
                                       → send to persistent CLI session → reply
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from typing import Optional

from qq_codex_bridge.bridge.codex import download_attachment
from qq_codex_bridge.bridge.session import SessionManager
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
# Show debug-level poll logs for the session module
logging.getLogger("qq_codex_bridge.bridge.session").setLevel(logging.DEBUG)
log = logging.getLogger(__name__)


def _session_id(msg: IncomingMessage) -> str:
    if msg.group_openid:
        return f"group:{msg.group_openid}"
    if msg.channel_id:
        return f"channel:{msg.channel_id}:user:{msg.author_id}"
    return f"dm:{msg.author_id}"


async def dispatch(
    payload: dict,
    config: AppConfig,
    session_mgr: SessionManager,
    sender: ReplySender,
) -> None:
    msg: Optional[IncomingMessage] = normalize(payload)
    if msg is None:
        return

    log.info("Message from %s: %r", msg.author_name, msg.content[:80])

    sid = _session_id(msg)
    sess = session_mgr.get(sid)

    # ── Built-in /commands ──────────────────────────────────────────────
    if msg.content.startswith("/"):
        result = handle_command(
            msg.content,
            session_workdir=sess.workdir,
            session_model=sess.model,
            default_workdir=config.codex.default_workdir,
        )
        if result is not None:
            # Apply workdir / model change (restarts the CLI process)
            workdir_changed = result.new_workdir != sess.workdir
            model_changed = result.new_model is not None and result.new_model != sess.model
            if workdir_changed or model_changed:
                sess.switch(
                    model=result.new_model or sess.model,
                    workdir=result.new_workdir,
                )
            await sender.send(result.reply, source=msg)
            return

    # ── Download image attachments (mention path in prompt) ─────────────
    image_notes = ""
    if msg.attachments:
        tmp_dir = tempfile.mkdtemp(prefix="qq_attach_")
        paths = []
        for att in msg.attachments:
            if att.content_type.startswith("image/"):
                path = await download_attachment(att.url, tmp_dir)
                if path:
                    paths.append(path)
        if paths:
            image_notes = "\n[附件图片: " + ", ".join(paths) + "]"

    prompt = msg.content + image_notes
    if not prompt.strip():
        await sender.send("(空消息)", source=msg)
        return

    # ── Forward to persistent CLI session ───────────────────────────────
    loop = asyncio.get_event_loop()
    try:
        reply = await loop.run_in_executor(
            None,
            lambda: sess.send_recv(prompt),
        )
    except FileNotFoundError as exc:
        reply = f"[错误] {exc}"
    except Exception as exc:
        log.exception("CLI session error")
        reply = f"[错误] {exc}"

    await sender.send(reply or "(无输出)", source=msg)


async def main() -> None:
    config = load_config()

    session_mgr = SessionManager(default_workdir=config.codex.default_workdir)
    sender = ReplySender(
        app_id=config.bot.app_id,
        app_secret=config.bot.app_secret,
        sandbox=config.bot.sandbox,
        chunk_size=config.codex.reply_chunk_size,
        max_retries=config.codex.reply_max_retries,
    )

    async def _dispatch(payload: dict) -> None:
        await dispatch(payload, config, session_mgr, sender)

    client = BotGatewayClient(
        app_id=config.bot.app_id,
        app_secret=config.bot.app_secret,
        sandbox=config.bot.sandbox,
        dispatch=_dispatch,
    )

    log.info("QQ Codex Bridge starting (WebSocket mode)...")
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
