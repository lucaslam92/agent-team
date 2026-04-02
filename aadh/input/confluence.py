"""
Confluence fetcher — supports page URL (Cloud and Server).

Fetches page title + body, strips HTML to plain text.
Handles both:
  - Cloud:  https://xxx.atlassian.net/wiki/spaces/SPACE/pages/123456/Title
  - Server: https://wiki.company.com/display/SPACE/Page+Title
"""

from __future__ import annotations
import os
import re
import urllib.request
import urllib.parse
import json
import base64
import html

from aadh.input.parser import TaskSpec, InputType


_CLOUD_PAGE_RE  = re.compile(r"https?://([^/]+)/wiki/(?:spaces/[^/]+/)?pages/(\d+)", re.I)
_SERVER_PAGE_RE = re.compile(r"https?://([^/]+)/display/([^/]+)/(.+)", re.I)


def fetch(raw: str, cfg: dict) -> TaskSpec:
    url = raw.strip()

    cloud_m  = _CLOUD_PAGE_RE.search(url)
    server_m = _SERVER_PAGE_RE.search(url) if not cloud_m else None

    if cloud_m:
        base_url = f"https://{cloud_m.group(1)}"
        page_id  = cloud_m.group(2)
        data = _api_get_cloud(base_url, page_id, cfg)
    elif server_m:
        base_url  = f"https://{server_m.group(1)}"
        space_key = server_m.group(2)
        title     = urllib.parse.unquote_plus(server_m.group(3))
        data = _api_get_server_by_title(base_url, space_key, title, cfg)
    else:
        raise ValueError(f"Cannot parse Confluence URL: {url!r}")

    title   = data.get("title", "Confluence Page")
    body    = data.get("body", {}).get("storage", {}).get("value", "")
    text    = _html_to_text(body)

    description = f"# {title}\n\n{text}".strip()

    return TaskSpec(
        raw_input=raw,
        input_type=InputType.CONFLUENCE,
        title=title,
        description=description,
        source_url=url,
        metadata={"page_id": data.get("id", ""), "space": data.get("space", {}).get("key", "")},
    )


# ── API calls ─────────────────────────────────────────────────────────────────

def _auth_header(cfg: dict) -> str:
    email     = cfg.get("email")     or os.environ.get("CONFLUENCE_EMAIL", "") \
                                     or os.environ.get("JIRA_EMAIL", "")
    api_token = cfg.get("api_token") or os.environ.get("CONFLUENCE_API_TOKEN", "") \
                                     or os.environ.get("JIRA_API_TOKEN", "")
    if not email or not api_token:
        raise ValueError(
            "Confluence credentials not found. Set CONFLUENCE_EMAIL + CONFLUENCE_API_TOKEN "
            "(or JIRA_EMAIL + JIRA_API_TOKEN) or add them to settings.yaml [input.confluence]."
        )
    creds = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    return f"Basic {creds}"


def _get(url: str, auth: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Authorization": auth, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _api_get_cloud(base_url: str, page_id: str, cfg: dict) -> dict:
    auth = _auth_header(cfg)
    url  = f"{base_url}/wiki/rest/api/content/{page_id}?expand=body.storage,space"
    return _get(url, auth)


def _api_get_server_by_title(base_url: str, space_key: str, title: str, cfg: dict) -> dict:
    auth  = _auth_header(cfg)
    enc   = urllib.parse.quote(title)
    url   = (f"{base_url}/rest/api/content"
             f"?spaceKey={space_key}&title={enc}&expand=body.storage,space")
    data  = _get(url, auth)
    results = data.get("results", [])
    if not results:
        raise ValueError(f"Confluence page not found: {title!r} in space {space_key!r}")
    return results[0]


# ── HTML → plain text ─────────────────────────────────────────────────────────

_TAG_RE    = re.compile(r"<[^>]+>")
_SPACE_RE  = re.compile(r" {2,}")
_NL_RE     = re.compile(r"\n{3,}")

_BLOCK_TAGS = re.compile(
    r"</?(p|div|h[1-6]|li|tr|br|blockquote|pre|ul|ol|table)[^>]*>", re.I
)


def _html_to_text(html_str: str) -> str:
    # Replace block-level closing tags with newlines before stripping
    text = _BLOCK_TAGS.sub("\n", html_str)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = _SPACE_RE.sub(" ", text)
    text = _NL_RE.sub("\n\n", text)
    return text.strip()
