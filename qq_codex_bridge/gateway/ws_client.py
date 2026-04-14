"""
QQ Official Bot WebSocket Gateway Client.

Protocol flow
-------------
1. GET /gateway/bot  → { "url": "wss://..." }
2. Connect to wss URL
3. Receive op=10 Hello  → { "heartbeat_interval": N ms }
4. Send   op=2  Identify with token + intents
5. Receive op=0  READY  → session_id, shard, user info
6. Loop:
     - Receive op=0  Dispatch → forward event to dispatch callback
     - Receive op=11 Heartbeat ACK → ok
     - Receive op=7  Reconnect   → reconnect with Resume
     - Receive op=9  Invalid Session → full re-identify
     - Every heartbeat_interval ms: Send op=1 Heartbeat with last seq

Reconnect strategy
------------------
- On disconnect: exponential back-off (2s, 4s, 8s … cap 60s)
- If session_id is still valid: send op=6 Resume to avoid replaying
  missed events manually (QQ will replay them automatically)
- If Resume is rejected (op=9): fall back to full Identify

Intents bitmask (add as needed)
--------------------------------
  GUILDS                = 1 << 0
  AT_MESSAGE_CREATE     = 1 << 30   # guild @bot messages
  GROUP_AT_MESSAGE      = 1 << 25   # group @bot messages
  C2C_MESSAGE           = 1 << 26   # private/C2C messages
  DIRECT_MESSAGE        = 1 << 12   # DM in guild
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Callable, Awaitable, Optional

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent flags
# ---------------------------------------------------------------------------
INTENT_AT_MESSAGE = 1 << 30
INTENT_GROUP_AT_MESSAGE = 1 << 25
INTENT_C2C_MESSAGE = 1 << 26
INTENT_DIRECT_MESSAGE = 1 << 12

DEFAULT_INTENTS = (
    INTENT_AT_MESSAGE
    | INTENT_GROUP_AT_MESSAGE
    | INTENT_C2C_MESSAGE
    | INTENT_DIRECT_MESSAGE
)

_QQ_API_BASE = "https://api.sgroup.qq.com"
_QQ_SANDBOX_BASE = "https://sandbox.api.sgroup.qq.com"


class BotGatewayClient:
    """
    Long-lived WebSocket client for the QQ Official Bot gateway.

    Parameters
    ----------
    app_id:     QQ application ID (string)
    token:      QQ bot token
    sandbox:    Use sandbox API endpoints
    intents:    Bitmask of subscribed event intents
    dispatch:   Async callback invoked for each op=0 event payload (dict)
    """

    def __init__(
        self,
        *,
        app_id: str,
        token: str,
        sandbox: bool = False,
        intents: int = DEFAULT_INTENTS,
        dispatch: Callable[[dict], Awaitable[None]],
    ) -> None:
        self._app_id = app_id
        self._token = token
        self._base = _QQ_SANDBOX_BASE if sandbox else _QQ_API_BASE
        self._intents = intents
        self._dispatch = dispatch

        # Runtime state
        self._session_id: Optional[str] = None
        self._seq: Optional[int] = None          # last received sequence number
        self._heartbeat_interval: float = 41.25  # seconds (default QQ value)
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Connect and run forever, reconnecting on failure."""
        backoff = 2.0
        while True:
            try:
                await self._connect_loop()
                backoff = 2.0  # reset on clean exit (shouldn't happen)
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
            max_size=10 * 1024 * 1024,  # 10 MB
            ping_interval=None,          # we manage heartbeats ourselves
        ) as ws:
            await self._handle_connection(ws)

    async def _handle_connection(self, ws) -> None:
        async for raw in ws:
            payload = json.loads(raw)
            op = payload.get("op")
            data = payload.get("d", {})
            seq = payload.get("s")
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
        log.info("Hello received — heartbeat interval: %.2fs", self._heartbeat_interval)

        # Cancel previous heartbeat loop if reconnecting
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))

        if self._session_id and self._seq is not None:
            # Resume existing session
            log.info("Resuming session %s at seq %s", self._session_id, self._seq)
            await ws.send(json.dumps({
                "op": 6,
                "d": {
                    "token": f"QQBot {self._token}",
                    "session_id": self._session_id,
                    "seq": self._seq,
                },
            }))
        else:
            # Fresh identify
            log.info("Identifying (app_id=%s, intents=%d)", self._app_id, self._intents)
            await ws.send(json.dumps({
                "op": 2,
                "d": {
                    "token": f"QQBot {self._token}",
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
                "READY — bot: %s#%s, session: %s",
                user.get("username"),
                user.get("id"),
                self._session_id,
            )
            return

        if event_type == "RESUMED":
            log.info("RESUMED — session restored")
            return

        # Forward all other events to the application layer
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
                heartbeat = json.dumps({"op": 1, "d": self._seq})
                await ws.send(heartbeat)
                log.debug("Heartbeat sent (seq=%s)", self._seq)
        except (ConnectionClosed, asyncio.CancelledError):
            pass
        except Exception:
            log.exception("Heartbeat loop error")

    async def _fetch_gateway_url(self) -> str:
        """Call GET /gateway/bot to get the WebSocket URL."""
        headers = {"Authorization": f"QQBot {self._token}"}
        url = f"{self._base}/gateway/bot"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(f"Failed to fetch gateway URL (HTTP {resp.status}): {body}")
                data = await resp.json()
                ws_url = data.get("url", "")
                if not ws_url:
                    raise RuntimeError(f"Empty gateway URL in response: {data}")
                return ws_url
