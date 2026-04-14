"""
Session Context Manager — maintains per-conversation state.

Each unique conversation (group_openid or channel_id + author_id for DM)
gets its own context: current working directory, optional image paths
queued for the next codex call, etc.

The store is in-memory. On restart, sessions reset to defaults.
If persistence is needed later, swap the dict for Redis or SQLite.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """State for a single conversation."""
    session_id: str
    workdir: str
    # Paths of downloaded attachments queued for next codex call
    pending_files: List[str] = field(default_factory=list)


class SessionStore:
    """Thread-safe in-memory store for SessionContext objects."""

    def __init__(self, default_workdir: str) -> None:
        self._default_workdir = default_workdir
        self._sessions: Dict[str, SessionContext] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str) -> SessionContext:
        """Return the session, creating it with defaults if new."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionContext(
                    session_id=session_id,
                    workdir=self._default_workdir,
                )
                log.debug("New session: %s", session_id)
            return self._sessions[session_id]

    def update_workdir(self, session_id: str, new_workdir: str) -> None:
        ctx = self.get(session_id)
        with self._lock:
            ctx.workdir = new_workdir

    def add_pending_file(self, session_id: str, path: str) -> None:
        ctx = self.get(session_id)
        with self._lock:
            ctx.pending_files.append(path)

    def pop_pending_files(self, session_id: str) -> List[str]:
        """Return and clear all pending file paths for the session."""
        ctx = self.get(session_id)
        with self._lock:
            files = list(ctx.pending_files)
            ctx.pending_files.clear()
        return files

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


def make_session_id(group_openid: str, channel_id: str, author_id: str) -> str:
    """
    Build a stable session key from message routing fields.

    - Group messages: keyed by group (all members share a workdir per group)
    - DM / channel messages: keyed by author so each user has their own workdir
    """
    if group_openid:
        return f"group:{group_openid}"
    if channel_id:
        return f"channel:{channel_id}:user:{author_id}"
    return f"dm:{author_id}"
