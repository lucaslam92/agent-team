"""
QQ Official Bot WebSocket Gateway Client.

认证流程
--------
app_id + app_secret → AccessTokenManager → access_token
access_token 用于：
  - GET /gateway/bot  Authorization 头
  - op=2 Identify 的 token 字段（格式: "QQBot <access_token>"）
  - op=6 Resume 的 token 字段

Protocol flow
-------------
1. AccessTokenManager.get() → 获取/刷新 access_token
2. GET /gateway/bot          → { "url": "wss://..." }
3. Connect to wss URL
4. Receive op=10 Hello       → { "heartbeat_interval": N ms }
5. Send   op=2  Identify     → token + intents
6. Receive op=0  READY       → session_id, shard, user info
7. Loop:
     - op=0  Dispatch  → forward to dispatch callback
     - op=11 Heartbeat ACK → ok
     - op=7  Reconnect → reconnect with Resume
     - op=9  Invalid Session → full re-identify
     - Every heartbeat_interval ms: Send op=1 Heartbeat

Reconnect strategy
------------------
- 断线 → 指数退避（2s, 4s … 上限 60s）
- session_id 有效 → op=6 Resume（QQ 自动补发丢失事件）
- Resume 被拒（op=9）→ 重新 Identify，丢弃旧 session
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Awaitable, Optional

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed

from qq_codex_bridge.gateway.token import AccessTokenManager

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent flags
# ---------------------------------------------------------------------------
INTENT_AT_MESSAGE       = 1 << 30   # 频道 @bot
INTENT_GROUP_AT_MESSAGE = 1 << 25   # 群聊 @bot
INTENT_C2C_MESSAGE      = 1 << 26   # 私聊
INTENT_DIRECT_MESSAGE   = 1 << 12   # 频道私信

DEFAULT_INTENTS = (
    INTENT_AT_MESSAGE
    | INTENT_GROUP_AT_MESSAGE
    | INTENT_C2C_MESSAGE
    | INTENT_DIRECT_MESSAGE
)

_QQ_API_BASE    = "https://api.sgroup.qq.com"
_QQ_SANDBOX_BASE = "https://sandbox.api.sgroup.qq.com"


class BotGatewayClient:
    """
    长连接 WebSocket 客户端。

    Parameters
    ----------
    app_id:     QQ AppID
    app_secret: QQ AppSecret（用于换取 access_token）
    sandbox:    使用沙箱 API 端点
    intents:    事件订阅位掩码
    dispatch:   收到 op=0 事件时的异步回调
    """

    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        sandbox: bool = False,
        intents: int = DEFAULT_INTENTS,
        dispatch: Callable[[dict], Awaitable[None]],
    ) -> None:
        self._app_id   = app_id
        self._base     = _QQ_SANDBOX_BASE if sandbox else _QQ_API_BASE
        self._intents  = intents
        self._dispatch = dispatch
        self._token_mgr = AccessTokenManager(app_id=app_id, app_secret=app_secret)

        # Runtime state
        self._session_id: Optional[str] = None
        self._seq: Optional[int] = None
        self._heartbeat_interval: float = 41.25
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """永久运行，断线自动重连（指数退避）。"""
        backoff = 2.0
        while True:
            try:
                await self._connect_loop()
                backoff = 2.0
            except Exception as exc:
                log.error("Gateway error: %s — reconnecting in %.0fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _connect_loop(self) -> None:
        ws_url = await self._fetch_gateway_url()
        log.info("Connecting to gateway: %s", ws_url)

        async with websockets.connect(
            ws_url,
            max_size=10 * 1024 * 1024,
            ping_interval=None,        # 由我们自己发心跳
        ) as ws:
            await self._handle_connection(ws)

    async def _handle_connection(self, ws) -> None:
        async for raw in ws:
            payload    = json.loads(raw)
            op         = payload.get("op")
            data       = payload.get("d", {})
            seq        = payload.get("s")
            event_type = payload.get("t", "")

            if seq is not None:
                self._seq = seq

            if op == 10:
                await self._on_hello(ws, data)
            elif op == 11:
                log.debug("Heartbeat ACK")
            elif op == 7:
                log.info("Server requested reconnect — closing for Resume")
                await ws.close()
                return
            elif op == 9:
                log.warning("Invalid session — will re-identify")
                self._session_id = None
                self._seq = None
                await asyncio.sleep(2)
                await ws.close()
                return
            elif op == 0:
                await self._on_dispatch(event_type, data, payload)
            else:
                log.debug("Unhandled op=%s", op)

    async def _on_hello(self, ws, data: dict) -> None:
        self._heartbeat_interval = data.get("heartbeat_interval", 41250) / 1000.0
        log.info("Hello — heartbeat interval: %.2fs", self._heartbeat_interval)

        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))

        # 每次 Hello 都重新取一次 token（可能已到期）
        access_token = await self._token_mgr.get()
        auth = f"QQBot {access_token}"

        if self._session_id and self._seq is not None:
            log.info("Resuming session %s at seq %s", self._session_id, self._seq)
            await ws.send(json.dumps({
                "op": 6,
                "d": {
                    "token": auth,
                    "session_id": self._session_id,
                    "seq": self._seq,
                },
            }))
        else:
            log.info("Identifying (app_id=%s, intents=%d)", self._app_id, self._intents)
            await ws.send(json.dumps({
                "op": 2,
                "d": {
                    "token": auth,
                    "intents": self._intents,
                    "shard": [0, 1],
                    "properties": {
                        "$os": "linux",
                        "$browser": "qq-codex-bridge",
                        "$device": "qq-codex-bridge",
                    },
                },
            }))

    async def _on_dispatch(self, event_type: str, data: dict, payload: dict) -> None:
        if event_type == "READY":
            self._session_id = data.get("session_id")
            user = data.get("user", {})
            log.info(
                "READY — bot: %s (%s), session: %s",
                user.get("username"), user.get("id"), self._session_id,
            )
            return

        if event_type == "RESUMED":
            log.info("RESUMED — session restored")
            return

        asyncio.create_task(self._safe_dispatch(payload))

    async def _safe_dispatch(self, payload: dict) -> None:
        try:
            await self._dispatch(payload)
        except Exception:
            log.exception("Unhandled error in dispatch callback")

    async def _heartbeat_loop(self, ws) -> None:
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                await ws.send(json.dumps({"op": 1, "d": self._seq}))
                log.debug("Heartbeat sent (seq=%s)", self._seq)
        except (ConnectionClosed, asyncio.CancelledError):
            pass
        except Exception:
            log.exception("Heartbeat loop error")

    async def _fetch_gateway_url(self) -> str:
        """GET /gateway/bot 获取 WebSocket 连接地址。"""
        access_token = await self._token_mgr.get()
        headers = {"Authorization": f"QQBot {access_token}"}
        url = f"{self._base}/gateway/bot"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(
                        f"Failed to fetch gateway URL (HTTP {resp.status}): {body}"
                    )
                data = await resp.json()
                ws_url = data.get("url", "")
                if not ws_url:
                    raise RuntimeError(f"Empty gateway URL in response: {data}")
                return ws_url
