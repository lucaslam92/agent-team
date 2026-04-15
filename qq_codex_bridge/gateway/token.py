"""
QQ Official Bot access_token manager.

QQ v2 认证流程：
  app_id + app_secret → POST /app/getAppAccessToken → access_token (TTL ~7200s)

access_token 用于：
  - WebSocket Identify / Resume 的 token 字段
  - REST API 的 Authorization: QQBot <access_token> 头

本模块维护一个单例 token，在过期前 60 秒自动刷新，所有调用方
通过 AccessTokenManager.get() 获取当前有效 token。
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import aiohttp

log = logging.getLogger(__name__)

_TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"


class AccessTokenManager:
    """
    异步 access_token 管理器。

    Usage:
        manager = AccessTokenManager(app_id="...", app_secret="...")
        token = await manager.get()   # 始终返回有效 token
    """

    def __init__(self, *, app_id: str, app_secret: str) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._token: Optional[str] = None
        self._expires_at: float = 0.0          # unix timestamp
        self._refresh_margin: float = 60.0     # 提前 60s 刷新
        self._lock = asyncio.Lock()

    async def get(self) -> str:
        """返回当前有效的 access_token，必要时自动刷新。"""
        async with self._lock:
            if self._needs_refresh():
                await self._refresh()
            return self._token  # type: ignore[return-value]

    def _needs_refresh(self) -> bool:
        return (
            self._token is None
            or time.time() >= self._expires_at - self._refresh_margin
        )

    async def _refresh(self) -> None:
        log.info("Fetching new access_token (app_id=%s)", self._app_id)
        payload = {"appId": self._app_id, "clientSecret": self._app_secret}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                _TOKEN_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(
                        f"Failed to get access_token (HTTP {resp.status}): {body}"
                    )
                data = await resp.json()

        token = data.get("access_token", "")
        expires_in = int(data.get("expires_in", 7200))

        if not token:
            raise RuntimeError(f"Empty access_token in response: {data}")

        self._token = token
        self._expires_at = time.time() + expires_in
        log.info(
            "access_token refreshed, expires in %ds (at %.0f)",
            expires_in,
            self._expires_at,
        )
