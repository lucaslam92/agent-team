#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-frontend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from frontend_design_lib import acceptance_items, feature_identity, load_json, load_repo_context_snapshot, requirement_lines, write_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate frontend scope alignment artifact.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--repo-context-snapshot", required=True)
    parser.add_argument("--knowbase-context", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    repo_context = load_repo_context_snapshot(args.repo_context_snapshot)
    knowbase_context = load_json(args.knowbase_context)
    feature_id, _ = feature_identity(final_prd)
    ac_refs = [item["ref"] for item in acceptance_items(final_prd)]
    lines = requirement_lines(final_prd)
    payload = {
        "feature_id": feature_id,
        "platform": repo_context.get("platform", "web"),
        "frontend_responsibilities": [
            {"id": "ui_flow", "summary": "Own page rendering, interaction, and local UX states.", "acceptance_refs": ac_refs},
            {"id": "contract_consumption", "summary": "Consume backend contract and map it to user-facing states.", "acceptance_refs": ac_refs},
        ],
        "backend_responsibilities": [
            {"id": "backend_contract", "summary": "Own system behavior, APIs, events, and write-side consistency.", "acceptance_refs": ac_refs}
        ],
        "shared_contracts": [
            {"id": "frontend_contract_view", "summary": "Frontend-facing consumption contract.", "acceptance_refs": ac_refs}
        ],
        "out_of_scope": ["Backend implementation details.", "Visual redesign outside the current feature scope."],
        "assumptions": [gap["summary"] for gap in knowbase_context.get("unresolved_gaps", [])],
        "open_issues": [line for line in lines if "figma" in line.lower()],
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
