#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-backend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from backend_design_lib import (  # noqa: E402
    acceptance_items,
    feature_identity,
    load_json,
    load_repo_context_snapshot,
    requirement_lines,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate backend scope alignment artifact.")
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

    requirement_text = requirement_lines(final_prd)
    backend_responsibilities = [
        {
            "id": "backend_contract",
            "summary": f"Own backend service behavior for {repo_context.get('primary_service', 'the target service')}.",
            "acceptance_refs": ac_refs,
        }
    ]
    if any("event" in line.lower() for line in requirement_text):
        backend_responsibilities.append(
            {
                "id": "backend_events",
                "summary": "Design backend event publication and async processing boundaries.",
                "acceptance_refs": ac_refs,
            }
        )

    frontend_responsibilities = [
        {
            "id": "frontend_consumption",
            "summary": "Consume backend contract and render user-facing interaction states.",
            "acceptance_refs": ac_refs,
        }
    ]
    shared_contracts = [
        {"id": "api_contract", "summary": "Machine-readable backend API/event/job contract.", "owner": "backend"},
        {"id": "acceptance_mapping", "summary": "Shared acceptance criteria to design/test mapping.", "owner": "shared"},
    ]
    assumptions = [gap["summary"] for gap in knowbase_context.get("unresolved_gaps", [])]
    if repo_context.get("existing_apis"):
        assumptions.append("Existing API inventory was used to avoid overlapping contracts.")
    payload = {
        "feature_id": feature_id,
        "backend_responsibilities": backend_responsibilities,
        "frontend_responsibilities": frontend_responsibilities,
        "shared_contracts": shared_contracts,
        "out_of_scope": [
            "Frontend UI implementation details.",
            "Production rollout execution.",
        ],
        "assumptions": assumptions,
        "open_issues": [
            gap["summary"]
            for gap in knowbase_context.get("unresolved_gaps", [])
            if gap.get("severity") == "high"
        ],
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
