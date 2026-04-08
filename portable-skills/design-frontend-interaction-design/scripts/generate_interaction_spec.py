#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-frontend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from frontend_design_lib import acceptance_items, feature_identity, load_json, requirement_lines, write_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate interaction_spec.json.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--contract-view", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    contract_view = load_json(args.contract_view)
    feature_id, feature_name = feature_identity(final_prd)
    requirements = requirement_lines(final_prd)
    acceptance = acceptance_items(final_prd)
    payload = {
        "feature_id": feature_id,
        "user_actions": [f"Trigger {feature_name} primary interaction.", "Retry failed request when safe."],
        "validations": ["Validate required fields before submit.", "Show inline validation for blocking input issues."],
        "feedback": ["Show pending, success, and failure feedback tied to contract states."],
        "optimistic_updates": ["Avoid optimistic mutation unless backend contract explicitly supports it."],
        "retry_patterns": ["Provide manual retry for retryable failures."] if contract_view.get("consumed_apis") else [],
        "degraded_experience": ["Use fallback empty/error states when backend data is unavailable."] + (["Disable advanced visual affordances until Figma details are confirmed."] if any("figma" in line.lower() for line in requirements) else []),
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
