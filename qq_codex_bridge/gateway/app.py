"""
Event Gateway — FastAPI HTTP server that receives QQ webhook events.

Responsibilities:
  1. Validate Ed25519 signature on every request
  2. Respond immediately to URL-verification challenges
  3. Parse the event type and dispatch to the message router
  4. Return HTTP 200 quickly so QQ doesn't retry

All heavy lifting (codex exec, reply) runs in a background task so
the HTTP response is always fast.
"""
from __future__ import annotations

import json
import logging
from typing import Callable, Awaitable

from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from qq_codex_bridge.config import AppConfig
from qq_codex_bridge.gateway.models import EventType
from qq_codex_bridge.gateway.signature import verify_signature, build_challenge_response

log = logging.getLogger(__name__)


def create_app(
    config: AppConfig,
    dispatch: Callable[[dict, AppConfig], Awaitable[None]],
) -> FastAPI:
    """
    Factory — creates the FastAPI app.

    Parameters
    ----------
    config:
        Loaded AppConfig.
    dispatch:
        Async coroutine that processes a parsed QQ event dict.
        Signature: async def dispatch(event: dict, config: AppConfig) -> None
    """
    app = FastAPI(title="QQ Codex Bridge", version="1.0.0")

    @app.post(config.gateway.path)
    async def webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
        body = await request.body()

        # --- Signature validation ---
        sig = request.headers.get("X-Signature-Ed25519", "")
        ts = request.headers.get("X-Signature-Timestamp", "")

        if not verify_signature(
            bot_secret=config.bot.secret,
            timestamp=ts,
            body=body,
            signature=sig,
        ):
            log.warning("Rejected request — bad signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

        # --- Parse payload ---
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            log.error("Non-JSON body received")
            raise HTTPException(status_code=400, detail="Invalid JSON")

        op = payload.get("op")
        event_type = payload.get("t", "")
        data = payload.get("d", {})

        # op=13 → URL verification challenge
        if op == 13:
            challenge = data.get("plain", "")
            log.info("URL verification challenge received")
            return JSONResponse(build_challenge_response(challenge))

        # op=0 → normal dispatch event
        if op == 0:
            log.info("Received event: %s", event_type)
            background_tasks.add_task(dispatch, payload, config)
            return Response(status_code=200)

        # op=12 → heartbeat ACK — nothing to do
        log.debug("Received op=%s (no action)", op)
        return Response(status_code=200)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app
