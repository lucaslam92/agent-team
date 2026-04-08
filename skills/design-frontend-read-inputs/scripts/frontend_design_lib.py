#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


STACK_KEYWORDS = {
    "language": ["typescript", "javascript", "kotlin", "swift", "dart"],
    "framework": ["react", "next", "vue", "svelte", "jetpack compose", "swiftui", "flutter"],
    "routing": ["react router", "router", "navigation", "deeplink"],
    "state_management": ["redux", "zustand", "mobx", "recoil", "context", "viewmodel"],
    "design_system": ["material", "ant design", "chakra", "tailwind", "design token"],
}


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, data: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def flatten_strings(value: Any) -> list[str]:
    items: list[str] = []
    if isinstance(value, str):
        text = value.strip()
        if text:
            items.append(text)
        return items
    if isinstance(value, dict):
        for nested in value.values():
            items.extend(flatten_strings(nested))
        return items
    if isinstance(value, list):
        for nested in value:
            items.extend(flatten_strings(nested))
    return items


def unique_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = item.strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def slugify(value: str, fallback: str = "item") -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or fallback


def feature_identity(final_prd: dict[str, Any]) -> tuple[str, str]:
    feature_id = (
        final_prd.get("feature_id")
        or final_prd.get("id")
        or slugify(str(final_prd.get("title") or final_prd.get("name") or "frontend_feature"))
    )
    feature_name = str(final_prd.get("feature_name") or final_prd.get("title") or final_prd.get("name") or feature_id)
    return str(feature_id), feature_name


def acceptance_items(final_prd: dict[str, Any]) -> list[dict[str, str]]:
    raw = as_list(final_prd.get("acceptance_criteria"))
    items: list[dict[str, str]] = []
    for index, item in enumerate(raw, start=1):
        if isinstance(item, dict):
            ref = str(item.get("id") or item.get("ref") or f"AC-{index:03d}")
            summary = str(item.get("summary") or item.get("text") or item.get("name") or ref)
        else:
            ref = f"AC-{index:03d}"
            summary = str(item)
        items.append({"ref": ref, "summary": summary})
    if not items:
        items.append({"ref": "AC-001", "summary": "Follow final_prd baseline acceptance criteria."})
    return items


def requirement_lines(final_prd: dict[str, Any]) -> list[str]:
    keys = [
        "functional_requirements",
        "non_functional_requirements",
        "user_flows",
        "platform_contract",
        "dependency_contract",
        "state_contract",
        "scope",
    ]
    lines: list[str] = []
    for key in keys:
        lines.extend(flatten_strings(final_prd.get(key)))
    return unique_strings(lines)


def merge_repo_context(
    repo_context: dict[str, Any],
    ui_inventory: dict[str, Any] | None,
    existing_routes: dict[str, Any] | None,
    architecture_constraints: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(repo_context)
    inventory = ui_inventory or {}
    routes = existing_routes or {}
    constraints = architecture_constraints or {}
    merged["pages"] = as_list(merged.get("pages")) or as_list(inventory.get("pages"))
    merged["components"] = as_list(merged.get("components")) or as_list(inventory.get("components"))
    merged["routes"] = as_list(merged.get("routes")) or as_list(routes.get("routes"))
    merged["state_management"] = as_list(merged.get("state_management")) or as_list(inventory.get("state_management"))
    merged["design_system"] = as_list(merged.get("design_system")) or as_list(inventory.get("design_system"))
    merged["architecture_constraints"] = as_list(merged.get("architecture_constraints")) or as_list(constraints.get("architecture_constraints"))
    return merged


def missing_repo_fields(repo_context: dict[str, Any]) -> list[str]:
    required = [
        "repo_id",
        "repo_name",
        "platform",
        "primary_stack",
        "module_roots",
        "pages",
        "routes",
        "components",
        "state_management",
        "architecture_constraints",
    ]
    missing: list[str] = []
    for key in required:
        value = repo_context.get(key)
        if value is None or value == "" or value == []:
            missing.append(key)
    return missing


def needs_contract(final_prd: dict[str, Any]) -> bool:
    text = " ".join(requirement_lines(final_prd)).lower()
    keywords = ["api", "event", "async", "submit", "load", "refresh"]
    return any(keyword in text for keyword in keywords)


def scan_markdown_notes(path: str | Path, limit: int = 12) -> list[str]:
    notes: list[str] = []
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^[-*]\s*", "", line)
        if line and line not in notes:
            notes.append(line)
        if len(notes) >= limit:
            break
    return notes


def detect_stack(notes: list[str]) -> dict[str, list[str]]:
    stack = {key: [] for key in STACK_KEYWORDS}
    combined = " ".join(notes).lower()
    for category, keywords in STACK_KEYWORDS.items():
        hits = [keyword for keyword in keywords if keyword in combined]
        stack[category] = hits
    return stack


def context_note(note_id: str, summary: str, source_ref: str, scope: str) -> dict[str, str]:
    return {"id": note_id, "summary": summary, "source_ref": source_ref, "scope": scope}


def ref_entry(ref_id: str, path: str, kind: str) -> dict[str, str]:
    return {"ref_id": ref_id, "path": path, "kind": kind}


def gap_entry(gap_id: str, summary: str, severity: str, recommended_action: str) -> dict[str, str]:
    return {"id": gap_id, "summary": summary, "severity": severity, "recommended_action": recommended_action}


def load_repo_context_snapshot(path: str | Path) -> dict[str, Any]:
    payload = load_json(path)
    return payload.get("repo_context", payload)


def parse_contract_ids(path: str | Path) -> dict[str, list[str]]:
    ids = {"api": [], "event": [], "job": []}
    pattern = re.compile(r"^\s*id:\s*([A-Za-z0-9_.-]+)\s*$")
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        item_id = match.group(1)
        if item_id.startswith("api_"):
            ids["api"].append(item_id)
        elif item_id.startswith("event_"):
            ids["event"].append(item_id)
        elif item_id.startswith("job_"):
            ids["job"].append(item_id)
    return ids
