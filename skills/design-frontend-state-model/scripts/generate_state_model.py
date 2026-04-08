#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-frontend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from frontend_design_lib import feature_identity, load_json, write_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate state_model.json.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--contract-view", required=True)
    parser.add_argument("--page-map", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    contract_view = load_json(args.contract_view)
    page_map = load_json(args.page_map)
    feature_id, feature_name = feature_identity(final_prd)
    payload = {
        "feature_id": feature_id,
        "server_state": ["remote_data", "submit_result"] if contract_view.get("consumed_apis") else [],
        "view_state": [f"{feature_name}_page_ready", f"{feature_name}_error_visible"],
        "transient_state": ["is_submitting", "focused_field"],
        "derived_state": ["can_submit", "show_empty_state"],
        "state_transitions": [
            {"from": "idle", "to": "loading", "trigger": "request_start"},
            {"from": "loading", "to": "ready", "trigger": "request_success"},
            {"from": "loading", "to": "error", "trigger": "request_failure"},
        ],
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
