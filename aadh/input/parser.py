"""
Input parser — detects source type and normalizes to a TaskSpec.

Supported inputs:
  1. Jira ticket URL or key   e.g. "https://xxx.atlassian.net/browse/AND-123" or "AND-123"
  2. Confluence page URL      e.g. "https://xxx.atlassian.net/wiki/spaces/ENG/pages/123456"
  3. Local .md file path      e.g. "./tasks/feature.md" or "/abs/path/task.md"
  4. Plain text               anything else — used as-is

All sources produce a TaskSpec with a normalized description
that the Planner consumes.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class InputType(str, Enum):
    JIRA       = "jira"
    CONFLUENCE = "confluence"
    MARKDOWN   = "markdown"
    TEXT       = "text"


@dataclass
class TaskSpec:
    raw_input: str          # Original string the user passed in
    input_type: InputType
    title: str              # Short title / summary
    description: str        # Full normalized text (what the Planner sees)
    source_url: str = ""    # Original URL, if any
    metadata: dict = None   # Extra fields (Jira priority, labels, etc.)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ── Detection ─────────────────────────────────────────────────────────────────

_JIRA_URL_RE   = re.compile(r"https?://[^/]+/browse/([A-Z]+-\d+)", re.I)
_JIRA_KEY_RE   = re.compile(r"^[A-Z]{2,10}-\d+$")
_CONF_URL_RE   = re.compile(r"https?://[^/]+/wiki/", re.I)


def detect(raw: str) -> InputType:
    s = raw.strip()
    if _JIRA_URL_RE.search(s) or _JIRA_KEY_RE.match(s):
        return InputType.JIRA
    if _CONF_URL_RE.search(s):
        return InputType.CONFLUENCE
    # Local .md file?
    if s.endswith(".md") and Path(s).exists():
        return InputType.MARKDOWN
    return InputType.TEXT


def parse(raw: str, input_cfg: dict | None = None) -> TaskSpec:
    """
    Parse raw user input into a TaskSpec.

    input_cfg mirrors the [input] section of settings.yaml:
      jira.base_url, jira.email, jira.api_token
      confluence.base_url, confluence.email, confluence.api_token
    """
    cfg = input_cfg or {}
    kind = detect(raw.strip())

    if kind == InputType.JIRA:
        from aadh.input.jira import fetch
        return fetch(raw.strip(), cfg.get("jira", {}))

    if kind == InputType.CONFLUENCE:
        from aadh.input.confluence import fetch
        return fetch(raw.strip(), cfg.get("confluence", {}))

    if kind == InputType.MARKDOWN:
        from aadh.input.markdown import fetch
        return fetch(raw.strip())

    # Plain text
    return TaskSpec(
        raw_input=raw,
        input_type=InputType.TEXT,
        title=raw[:80],
        description=raw,
    )
