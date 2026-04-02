"""
Jira fetcher — supports ticket URL or bare key (e.g. AND-123).

Fetches: summary, description, acceptance criteria (from custom field or
description body), priority, labels, and linked issues.

Auth: Basic Auth (email + API token) — the only method Jira Cloud supports.
"""

from __future__ import annotations
import os
import re
import urllib.request
import urllib.parse
import json
import base64

from aadh.input.parser import TaskSpec, InputType


_JIRA_KEY_RE  = re.compile(r"[A-Z]{2,10}-\d+", re.I)
_JIRA_URL_RE  = re.compile(r"https?://([^/]+)/browse/([A-Z]+-\d+)", re.I)


def fetch(raw: str, cfg: dict) -> TaskSpec:
    base_url, issue_key = _resolve(raw, cfg)
    data = _api_get(base_url, f"/rest/api/2/issue/{issue_key}", cfg)

    fields  = data.get("fields", {})
    summary = fields.get("summary", issue_key)

    # Build description: combine Jira description + acceptance criteria field
    desc_parts = [f"# {summary}", ""]

    raw_desc = _extract_text(fields.get("description") or "")
    if raw_desc:
        desc_parts += [raw_desc, ""]

    # Common custom field names for acceptance criteria
    ac = _find_acceptance_criteria(fields)
    if ac:
        desc_parts += ["## Acceptance Criteria", ac, ""]

    priority = (fields.get("priority") or {}).get("name", "")
    labels   = fields.get("labels", [])
    if priority:
        desc_parts.append(f"Priority: {priority}")
    if labels:
        desc_parts.append(f"Labels: {', '.join(labels)}")

    return TaskSpec(
        raw_input=raw,
        input_type=InputType.JIRA,
        title=summary,
        description="\n".join(desc_parts).strip(),
        source_url=f"{base_url}/browse/{issue_key}",
        metadata={
            "issue_key": issue_key,
            "priority": priority,
            "labels": labels,
            "status": (fields.get("status") or {}).get("name", ""),
        },
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve(raw: str, cfg: dict) -> tuple[str, str]:
    """Return (base_url, issue_key)."""
    m = _JIRA_URL_RE.search(raw)
    if m:
        return f"https://{m.group(1)}", m.group(2).upper()

    key_match = _JIRA_KEY_RE.match(raw.strip())
    if key_match:
        base_url = cfg.get("base_url") or os.environ.get("JIRA_BASE_URL", "")
        if not base_url:
            raise ValueError(
                "Jira base_url not set. Add it to settings.yaml [input.jira.base_url] "
                "or set JIRA_BASE_URL env var."
            )
        return base_url.rstrip("/"), raw.strip().upper()

    raise ValueError(f"Cannot parse Jira input: {raw!r}")


def _api_get(base_url: str, path: str, cfg: dict) -> dict:
    email     = cfg.get("email")     or os.environ.get("JIRA_EMAIL", "")
    api_token = cfg.get("api_token") or os.environ.get("JIRA_API_TOKEN", "")
    if not email or not api_token:
        raise ValueError(
            "Jira credentials not found. Set JIRA_EMAIL + JIRA_API_TOKEN "
            "or add them to settings.yaml [input.jira]."
        )

    url = base_url.rstrip("/") + path
    creds = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Basic {creds}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _extract_text(value) -> str:
    """Handle both Jira wiki markup (string) and Atlassian Document Format (dict)."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        # Atlassian Document Format — walk the content tree
        return _adf_to_text(value).strip()
    return ""


def _adf_to_text(node: dict, depth: int = 0) -> str:
    """Recursively extract plain text from an ADF node."""
    node_type = node.get("type", "")
    text = node.get("text", "")
    parts: list[str] = []

    if text:
        parts.append(text)

    for child in node.get("content", []):
        parts.append(_adf_to_text(child, depth + 1))

    result = "".join(parts)

    # Add newlines for block elements
    if node_type in ("paragraph", "heading", "listItem", "bulletList", "orderedList"):
        result = result.strip() + "\n"

    return result


def _find_acceptance_criteria(fields: dict) -> str:
    """
    Look for acceptance criteria in common custom field names.
    Jira custom fields are named customfield_XXXXX — we check description
    and known label patterns.
    """
    candidates = [
        "customfield_10016",   # Common AC field
        "customfield_10014",
        "acceptance_criteria",
    ]
    for key in candidates:
        val = fields.get(key)
        if val:
            return _extract_text(val)

    # Also try to extract from description if it contains "Acceptance Criteria" header
    desc = _extract_text(fields.get("description") or "")
    m = re.search(r"acceptance criteria[:\s]*(.*?)(?=\n##|\n#|$)", desc, re.I | re.S)
    if m:
        return m.group(1).strip()

    return ""
