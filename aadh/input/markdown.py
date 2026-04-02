"""
Markdown file fetcher.

Reads a local .md file and extracts:
  - title from the first # heading (or filename)
  - full content as description

Supports frontmatter (--- key: value ---) for optional metadata.
"""

from __future__ import annotations
import re
from pathlib import Path

from aadh.input.parser import TaskSpec, InputType


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_H1_RE          = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def fetch(path_str: str) -> TaskSpec:
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Markdown file not found: {path}")

    raw = path.read_text(encoding="utf-8", errors="replace")

    # Strip frontmatter
    metadata: dict = {}
    fm_match = _FRONTMATTER_RE.match(raw)
    if fm_match:
        metadata = _parse_simple_yaml(fm_match.group(1))
        raw = raw[fm_match.end():]

    # Extract title
    h1_match = _H1_RE.search(raw)
    if h1_match:
        title = h1_match.group(1).strip()
    elif metadata.get("title"):
        title = str(metadata["title"])
    else:
        title = path.stem.replace("-", " ").replace("_", " ").title()

    return TaskSpec(
        raw_input=path_str,
        input_type=InputType.MARKDOWN,
        title=title,
        description=raw.strip(),
        source_url=str(path),
        metadata=metadata,
    )


def _parse_simple_yaml(text: str) -> dict:
    """
    Parse simple key: value frontmatter — no need for a full YAML library.
    Handles strings, lists (- item), and booleans.
    """
    result: dict = {}
    current_key: str | None = None
    current_list: list | None = None

    for line in text.splitlines():
        list_item = re.match(r"^\s+-\s+(.+)$", line)
        key_val   = re.match(r"^(\w[\w-]*):\s*(.*)?$", line)

        if list_item and current_key:
            if current_list is None:
                current_list = []
                result[current_key] = current_list
            current_list.append(list_item.group(1).strip())
        elif key_val:
            current_key  = key_val.group(1)
            value        = key_val.group(2).strip()
            current_list = None
            if value.lower() == "true":
                result[current_key] = True
            elif value.lower() == "false":
                result[current_key] = False
            elif value:
                result[current_key] = value

    return result
