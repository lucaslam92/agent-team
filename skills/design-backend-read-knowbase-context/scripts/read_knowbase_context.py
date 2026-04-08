#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-backend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from backend_design_lib import (  # noqa: E402
    context_note,
    detect_stack,
    feature_identity,
    gap_entry,
    load_json,
    ref_entry,
    scan_markdown_notes,
    unique_strings,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve backend knowbase context.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--knowledge-root", required=True)
    parser.add_argument("--repo-overlay-root")
    parser.add_argument("--output", required=True)
    return parser


def candidate_files(knowledge_root: Path, overlay_root: Path | None) -> list[tuple[str, Path, str]]:
    files: list[tuple[str, Path, str]] = [
        ("business_context", knowledge_root / "business" / "background.md", "global"),
        ("architecture_constraints", knowledge_root / "architecture" / "system_overview.md", "global"),
        ("architecture_constraints", knowledge_root / "architecture" / "backend_architecture.md", "global"),
        ("architecture_constraints", knowledge_root / "architecture" / "capacity_profile.md", "global"),
        ("backend_rules", knowledge_root / "rules" / "backend_rules.md", "global"),
        ("api_rules", knowledge_root / "rules" / "api_rules.md", "global"),
        ("testing_rules", knowledge_root / "rules" / "testing_rules.md", "global"),
    ]
    if overlay_root:
        files.extend(
            [
                ("backend_rules", overlay_root / "rules" / "local" / "backend_rules.md", "repo-local"),
                ("api_rules", overlay_root / "rules" / "local" / "api_rules.md", "repo-local"),
                ("testing_rules", overlay_root / "rules" / "local" / "testing_rules.md", "repo-local"),
            ]
        )
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
        "backend_rules": [],
        "api_rules": [],
        "data_rules": [],
        "testing_rules": [],
        "technical_stack": {
            "language": [],
            "framework": [],
            "storage": [],
            "cache": [],
            "mq": []
        },
        "anti_patterns": [],
        "resolved_references": [],
        "unresolved_gaps": [],
        "extraction_status": "ready",
    }

    all_notes: list[str] = []
    for category, path, scope in candidate_files(knowledge_root, overlay_root):
        if not path.exists():
            payload["unresolved_gaps"].append(
                gap_entry(
                    gap_id=f"missing_{path.stem}",
                    summary=f"Missing knowbase source: {path}",
                    severity="medium",
                    recommended_action=f"Add or restore {path.name} before final backend design review.",
                )
            )
            continue
        notes = scan_markdown_notes(path)
        payload["resolved_references"].append(ref_entry(f"{feature_id}_{path.stem}", str(path), category))
        for index, note in enumerate(notes, start=1):
            note_id = f"{path.stem}_{index:02d}"
            if category in payload:
                payload[category].append(context_note(note_id, note, str(path), scope))
            if category == "backend_rules" and any(keyword in note.lower() for keyword in ["data", "migration", "index", "cache"]):
                payload["data_rules"].append(context_note(f"data_{note_id}", note, str(path), scope))
            if any(keyword in note.lower() for keyword in ["禁止", "avoid", "anti-pattern", "不要"]):
                payload["anti_patterns"].append(context_note(f"anti_{note_id}", note, str(path), scope))
        all_notes.extend(notes)

    stack = detect_stack(all_notes)
    for key, values in stack.items():
        payload["technical_stack"][key] = unique_strings(values)

    critical_missing = not payload["architecture_constraints"] or not payload["backend_rules"]
    if critical_missing:
        payload["extraction_status"] = "blocked"
    elif payload["unresolved_gaps"]:
        payload["extraction_status"] = "degraded"

    write_json(args.output, payload)


if __name__ == "__main__":
    main()
