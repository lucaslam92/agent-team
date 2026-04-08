#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-frontend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from frontend_design_lib import context_note, detect_stack, feature_identity, gap_entry, load_json, ref_entry, scan_markdown_notes, unique_strings, write_json  # noqa: E402


PLATFORM_ARCH_FILE = {
    "web": "web_architecture.md",
    "android": "android_architecture.md",
    "ios": "ios_architecture.md",
    "cross_platform": "frontend_stack.md",
}

PLATFORM_RULE_FILE = {
    "web": "web_rules.md",
    "android": "android_rules.md",
    "ios": "ios_rules.md",
    "cross_platform": "frontend_component_rules.md",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve frontend knowbase context.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--knowledge-root", required=True)
    parser.add_argument("--platform", default="web")
    parser.add_argument("--repo-overlay-root")
    parser.add_argument("--output", required=True)
    return parser


def candidate_files(knowledge_root: Path, overlay_root: Path | None, platform: str) -> list[tuple[str, Path, str]]:
    files = [
        ("business_context", knowledge_root / "business" / "background.md", "global"),
        ("architecture_constraints", knowledge_root / "architecture" / "system_overview.md", "global"),
        ("architecture_constraints", knowledge_root / "architecture" / "frontend_stack.md", "global"),
        ("architecture_constraints", knowledge_root / "architecture" / PLATFORM_ARCH_FILE.get(platform, "web_architecture.md"), "platform"),
        ("frontend_rules", knowledge_root / "rules" / PLATFORM_RULE_FILE.get(platform, "web_rules.md"), "platform"),
        ("component_rules", knowledge_root / "rules" / "frontend_component_rules.md", "global"),
        ("api_rules", knowledge_root / "rules" / "api_rules.md", "global"),
        ("testing_rules", knowledge_root / "rules" / "testing_rules.md", "global"),
    ]
    if overlay_root:
        files.append(("frontend_rules", overlay_root / "rules" / "local" / f"{platform}_rules.md", "repo-local"))
    return files


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    feature_id, _ = feature_identity(final_prd)
    knowledge_root = Path(args.knowledge_root)
    overlay_root = Path(args.repo_overlay_root) if args.repo_overlay_root else None

    payload = {
        "business_context": [],
        "architecture_constraints": [],
        "frontend_rules": [],
        "api_rules": [],
        "testing_rules": [],
        "accessibility_rules": [],
        "component_rules": [],
        "technical_stack": {"language": [], "framework": [], "routing": [], "state_management": [], "design_system": []},
        "anti_patterns": [],
        "resolved_references": [],
        "unresolved_gaps": [],
        "extraction_status": "ready",
    }

    all_notes: list[str] = []
    for category, path, scope in candidate_files(knowledge_root, overlay_root, args.platform):
        if not path.exists():
            payload["unresolved_gaps"].append(
                gap_entry(f"missing_{path.stem}", f"Missing knowbase source: {path}", "medium", f"Add or restore {path.name} before final frontend design review.")
            )
            continue
        notes = scan_markdown_notes(path)
        payload["resolved_references"].append(ref_entry(f"{feature_id}_{path.stem}", str(path), category))
        for index, note in enumerate(notes, start=1):
            note_id = f"{path.stem}_{index:02d}"
            if category in payload:
                payload[category].append(context_note(note_id, note, str(path), scope))
            if any(keyword in note.lower() for keyword in ["accessibility", "a11y", "无障碍"]):
                payload["accessibility_rules"].append(context_note(f"a11y_{note_id}", note, str(path), scope))
            if any(keyword in note.lower() for keyword in ["anti-pattern", "不要", "avoid", "禁止"]):
                payload["anti_patterns"].append(context_note(f"anti_{note_id}", note, str(path), scope))
        all_notes.extend(notes)

    stack = detect_stack(all_notes)
    for key, values in stack.items():
        payload["technical_stack"][key] = unique_strings(values)

    if not payload["architecture_constraints"] or not payload["frontend_rules"]:
        payload["extraction_status"] = "blocked"
    elif payload["unresolved_gaps"]:
        payload["extraction_status"] = "degraded"

    write_json(args.output, payload)


if __name__ == "__main__":
    main()
