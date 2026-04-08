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
    parser = argparse.ArgumentParser(description="Generate data_binding_plan.json.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--contract-view", required=True)
    parser.add_argument("--state-model", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    contract_view = load_json(args.contract_view)
    state_model = load_json(args.state_model)
    feature_id, _ = feature_identity(final_prd)
    request_bindings = [
        {"source": api["id"], "target": "submit_action", "notes": "Trigger request from primary CTA."}
        for api in contract_view.get("consumed_apis", [])
    ]
    response_mapping = [
        {"source": api["id"], "target": "server_state.remote_data", "notes": "Map response payload into normalized UI state."}
        for api in contract_view.get("consumed_apis", [])
    ]
    error_mapping = [
        {"source": error["code"], "target": "view_state.error", "notes": error["user_message_strategy"]}
        for error in contract_view.get("ui_visible_errors", [])
    ]
    payload = {
        "feature_id": feature_id,
        "request_bindings": request_bindings,
        "response_mapping": response_mapping,
        "error_mapping": error_mapping,
        "cache_strategy": ["Use stale_while_revalidate or equivalent query cache strategy."] if contract_view.get("consumed_apis") else [],
        "polling_or_subscription": ["Refresh when async event or manual retry succeeds."] if contract_view.get("consumed_events") else [],
        "async_refresh_rules": ["Recompute derived state after every successful response."] if state_model.get("derived_state") else [],
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
