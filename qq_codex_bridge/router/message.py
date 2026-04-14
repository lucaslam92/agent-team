"""
Message Router — normalises raw QQ event payloads into IncomingMessage objects.

QQ message content arrives with embedded mentions like <@!123456>.
We strip those and any leading/trailing whitespace so the downstream
command and codex layers always receive clean text.

Attachment handling:
  - Images / videos are listed under `attachments` in the payload.
  - The router does NOT download them here; it records the URL.
    The codex bridge downloads them on demand before exec.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from qq_codex_bridge.gateway.models import (
    Attachment,
    EventType,
    IncomingMessage,
    MessageType,
)

log = logging.getLogger(__name__)

# Matches QQ @mention tokens: <@!USER_ID> or <@USER_ID>
_MENTION_RE = re.compile(r"<@!?[\w]+>")

# QQ content_type strings we treat as images
_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_VIDEO_TYPES = {"video/mp4", "video/mpeg", "video/quicktime"}


def _strip_mentions(text: str) -> str:
    """Remove @mention tokens and normalise whitespace."""
    cleaned = _MENTION_RE.sub("", text)
    return cleaned.strip()


def _parse_attachments(raw_attachments: list[dict]) -> list[Attachment]:
    attachments = []
    for att in raw_attachments:
        url = att.get("url", "")
        # QQ sometimes omits the scheme
        if url and not url.startswith("http"):
            url = "https://" + url
        attachments.append(
            Attachment(
                url=url,
                content_type=att.get("content_type", "application/octet-stream"),
                filename=att.get("filename", ""),
            )
        )
    return attachments


def _detect_message_type(text: str, attachments: list[Attachment]) -> MessageType:
    if not attachments:
        return MessageType.TEXT
    types = {a.content_type for a in attachments}
    has_image = bool(types & _IMAGE_TYPES)
    has_video = bool(types & _VIDEO_TYPES)
    has_text = bool(text)
    if has_text and (has_image or has_video):
        return MessageType.MIXED
    if has_video:
        return MessageType.VIDEO
    if has_image:
        return MessageType.IMAGE
    return MessageType.MIXED


def normalize(payload: dict) -> Optional[IncomingMessage]:
    """
    Convert a raw QQ webhook payload into a normalised IncomingMessage.
    Returns None if the event is not a message we handle.
    """
    event_type_str: str = payload.get("t", "")
    data: dict = payload.get("d", {})

    try:
        event_type = EventType(event_type_str)
    except ValueError:
        log.debug("Unhandled event type: %s", event_type_str)
        return None

    # Only handle message events
    message_events = {
        EventType.GROUP_AT_MESSAGE_CREATE,
        EventType.C2C_MESSAGE_CREATE,
        EventType.AT_MESSAGE_CREATE,
        EventType.DIRECT_MESSAGE_CREATE,
    }
    if event_type not in message_events:
        return None

    raw_content: str = data.get("content", "")
    content = _strip_mentions(raw_content)

    raw_attachments = data.get("attachments", [])
    attachments = _parse_attachments(raw_attachments)

    message_type = _detect_message_type(content, attachments)

    author = data.get("author", {})

    # Group events use group_openid; guild events use channel_id
    group_openid = data.get("group_openid", "")
    channel_id = data.get("channel_id", "")

    return IncomingMessage(
        event_type=event_type,
        message_id=data.get("id", ""),
        channel_id=channel_id,
        group_openid=group_openid,
        author_id=author.get("id", author.get("member_openid", "")),
        author_name=author.get("username", author.get("nickname", "unknown")),
        content=content,
        message_type=message_type,
        attachments=attachments,
        raw=data,
    )
