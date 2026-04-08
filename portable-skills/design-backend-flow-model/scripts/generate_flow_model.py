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
    requirement_lines,
    slugify,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate backend flow_model.json.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--api-contract", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    feature_id, feature_name = feature_identity(final_prd)
    requirements = requirement_lines(final_prd)
    acceptance = acceptance_items(final_prd)
    main_steps = [
        {"id": "step_request", "action": "Receive validated request.", "actor": "api", "writes": [], "publishes": []},
        {
            "id": "step_commit",
            "action": f"Persist {feature_name} state transition.",
            "actor": "domain_service",
            "writes": [f"{slugify(feature_name)}_state"],
            "publishes": [],
        },
    ]
    error_steps = [
        {"id": "step_validation_error", "action": "Return contract error response.", "actor": "api", "writes": [], "publishes": []}
    ]
    retry_steps = []
    compensation_steps = []
    if any("retry" in line.lower() or "job" in line.lower() for line in requirements):
        retry_steps.append(
            {
                "id": "step_retry_job",
                "action": "Retry failed transitions with bounded attempts.",
                "actor": "job",
                "writes": [],
                "publishes": [f"{slugify(feature_name)}.retry"],
            }
        )
    if any("compens" in line.lower() or "rollback" in line.lower() for line in requirements):
        compensation_steps.append(
            {
                "id": "step_compensate",
                "action": "Apply compensating state transition for partial failure.",
                "actor": "domain_service",
                "writes": [f"{slugify(feature_name)}_state"],
                "publishes": [f"{slugify(feature_name)}.compensated"],
            }
        )

    payload = {
        "feature_id": feature_id,
        "main_flows": [
            {"id": "main_flow", "summary": f"Primary backend flow for {feature_name}.", "steps": main_steps, "acceptance_refs": [item["ref"] for item in acceptance]}
        ],
        "error_flows": [
            {"id": "error_flow", "summary": "Validation and dependency failure handling.", "steps": error_steps, "acceptance_refs": [item["ref"] for item in acceptance]}
        ],
        "retry_flows": [
            {"id": "retry_flow", "summary": "Async retry recovery flow.", "steps": retry_steps, "acceptance_refs": [item["ref"] for item in acceptance]}
        ] if retry_steps else [],
        "compensation_flows": [
            {"id": "compensation_flow", "summary": "Compensating write flow.", "steps": compensation_steps, "acceptance_refs": [item["ref"] for item in acceptance]}
        ] if compensation_steps else [],
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
