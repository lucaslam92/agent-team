"""
Reply Sender — delivers OutgoingMessage objects back to QQ.

QQ Official Bot API has a message length limit (~2000 chars for group messages).
Long codex output is split into numbered chunks and sent sequentially.

Authorization: 使用 AccessTokenManager 获取 access_token，
               格式 "QQBot <access_token>"，token 过期自动刷新。

Retry strategy: exponential back-off (1s, 2s, 4s) on transient HTTP errors.
Permanent errors (4xx) are not retried.

QQ API endpoints used:
  Group:   POST /v2/groups/{group_openid}/messages
  Channel: POST /channels/{channel_id}/messages
  DM:      POST /v2/users/{openid}/messages
"""
from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

import aiohttp

from qq_codex_bridge.gateway.models import IncomingMessage, OutgoingMessage
from qq_codex_bridge.gateway.token import AccessTokenManager

log = logging.getLogger(__name__)

_QQ_OPENAPI_BASE = "https://api.sgroup.qq.com"
_QQ_SANDBOX_BASE = "https://sandbox.api.sgroup.qq.com"


class ReplySender:
    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        sandbox: bool = False,
        chunk_size: int = 1800,
        max_retries: int = 3,
    ) -> None:
        self._base = _QQ_SANDBOX_BASE if sandbox else _QQ_OPENAPI_BASE
        self._chunk_size = chunk_size
        self._max_retries = max_retries
        self._token_mgr = AccessTokenManager(app_id=app_id, app_secret=app_secret)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send(
        self,
        text: str,
        *,
        source: IncomingMessage,
        image_url: Optional[str] = None,
    ) -> None:
        """
        Send `text` (and optional image) as a reply to `source`.

        Long text is chunked automatically.  Each chunk is sent as a
        separate message with a "(1/N)" prefix so the user knows there's more.
        """
        chunks = self._chunk(text)
        total = len(chunks)

        for i, chunk in enumerate(chunks, 1):
            body = chunk if total == 1 else f"({i}/{total})\n{chunk}"
            msg = OutgoingMessage(
                text=body,
                image_url=image_url if i == 1 else "",
                reply_to_message_id=source.message_id,
                channel_id=source.channel_id,
                group_openid=source.group_openid,
                author_id=source.author_id,
            )
            await self._deliver(msg)
            if i < total:
                await asyncio.sleep(0.3)

    async def send_error(self, error: str, *, source: IncomingMessage) -> None:
        await self.send(f"[Error] {error}", source=source)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _chunk(self, text: str) -> List[str]:
        if len(text) <= self._chunk_size:
            return [text]
        chunks = []
        while text:
            chunks.append(text[: self._chunk_size])
            text = text[self._chunk_size :]
        return chunks

    async def _deliver(self, msg: OutgoingMessage) -> None:
        url, payload = self._build_request(msg)

        delay = 1.0
        for attempt in range(1, self._max_retries + 2):
            # 每次重试都重新取 token（可能已刷新）
            access_token = await self._token_mgr.get()
            headers = {
                "Authorization": f"QQBot {access_token}",
                "Content-Type": "application/json",
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status in (200, 201):
                            log.debug("Reply delivered (attempt %d)", attempt)
                            return
                        body = await resp.text()
                        if 400 <= resp.status < 500:
                            log.error(
                                "QQ API rejected message (HTTP %d): %s",
                                resp.status, body,
                            )
                            return  # 永久错误，不重试
                        log.warning(
                            "QQ API transient error (HTTP %d) attempt %d/%d: %s",
                            resp.status, attempt, self._max_retries + 1, body,
                        )
            except aiohttp.ClientError as exc:
                log.warning(
                    "Network error attempt %d/%d: %s",
                    attempt, self._max_retries + 1, exc,
                )

            if attempt <= self._max_retries:
                await asyncio.sleep(delay)
                delay *= 2

        log.error("Failed to deliver reply after %d attempts", self._max_retries + 1)

    def _build_request(self, msg: OutgoingMessage) -> tuple[str, dict]:
        content: dict = {}
        if msg.text:
            content["content"] = msg.text
        if msg.image_url:
            content["image"] = msg.image_url
        if msg.reply_to_message_id:
            content["msg_id"] = msg.reply_to_message_id

        if msg.group_openid:
            url = f"{self._base}/v2/groups/{msg.group_openid}/messages"
            payload = {**content, "msg_type": 0}
        elif msg.channel_id:
            url = f"{self._base}/channels/{msg.channel_id}/messages"
            payload = content
        else:
            url = f"{self._base}/v2/users/{msg.author_id}/messages"
            payload = {**content, "msg_type": 0}

        return url, payload
