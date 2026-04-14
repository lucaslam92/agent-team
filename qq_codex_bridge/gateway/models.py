"""
Typed dataclasses for all inter-module data exchange.
Mirrors the QQ Official Bot event payload structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    MIXED = "mixed"   # text + attachments


class EventType(str, Enum):
    # Group / channel message
    GROUP_AT_MESSAGE_CREATE = "GROUP_AT_MESSAGE_CREATE"
    C2C_MESSAGE_CREATE = "C2C_MESSAGE_CREATE"
    # Guild (频道) message
    AT_MESSAGE_CREATE = "AT_MESSAGE_CREATE"
    DIRECT_MESSAGE_CREATE = "DIRECT_MESSAGE_CREATE"
    # Lifecycle
    READY = "READY"
    RESUMED = "RESUMED"


@dataclass
class Attachment:
    """A file attached to a message (image, video, …)."""
    url: str
    content_type: str          # e.g. "image/png"
    filename: str = ""
    # Populated after download
    local_path: Optional[str] = None


@dataclass
class IncomingMessage:
    """Normalised inbound message — all source variants collapse to this."""
    event_type: EventType
    message_id: str
    # Conversation scope identifiers
    channel_id: str            # guild channel / group openid / "" for C2C
    group_openid: str          # non-empty for group events
    # Sender
    author_id: str
    author_name: str
    # Content
    content: str               # stripped plain text (@ mentions removed)
    message_type: MessageType
    attachments: list[Attachment] = field(default_factory=list)
    # Raw payload preserved for debugging
    raw: dict = field(default_factory=dict)


@dataclass
class OutgoingMessage:
    """Reply to be sent back through QQ."""
    # At least one of text / image_url must be set
    text: str = ""
    image_url: str = ""
    # Which message this is replying to
    reply_to_message_id: str = ""
    # Routing — filled in by the router from IncomingMessage
    channel_id: str = ""
    group_openid: str = ""
    author_id: str = ""
