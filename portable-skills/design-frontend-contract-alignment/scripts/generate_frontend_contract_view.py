#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-frontend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from frontend_design_lib import acceptance_items, feature_identity, load_json, parse_contract_ids, requirement_lines, slugify, write_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate frontend_contract_view.json.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--repo-context-snapshot", required=True)
    parser.add_argument("--frontend-scope", required=True)
    parser.add_argument("--api-contract")
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    scope = load_json(args.frontend_scope)
    feature_id, feature_name = feature_identity(final_prd)
    acceptance = acceptance_items(final_prd)
    requirements = requirement_lines(final_prd)
    contract_ids = parse_contract_ids(args.api_contract) if args.api_contract else {"api": [], "event": [], "job": []}

    consumed_apis = []
    if contract_ids["api"]:
        for index, api_id in enumerate(contract_ids["api"], start=1):
            consumed_apis.append(
                {
                    "id": api_id,
                    "name": f"{feature_name} API {index}",
                    "purpose": "Support frontend request/response interaction.",
                    "source_contract_ref": api_id,
                    "request_shape": {"type": "object"},
                    "response_shape": {"type": "object"},
                    "ui_states": ["idle", "submitting", "success"],
                    "error_states": ["validation_error", "server_error"],
                    "retry_behavior": "manual_retry",
                    "optimistic_behavior": "disabled_by_default",
                    "cache_behavior": "stale_while_revalidate",
                    "acceptance_refs": [item["ref"] for item in acceptance],
                    "test_requirements": ["contract_test", "integration_test"],
                }
            )
    fallback_contracts = []
    if not consumed_apis:
        for index, item in enumerate(acceptance, start=1):
            fallback_contracts.append(
                {
                    "id": f"fallback_{slugify(item['summary'], f'cmd_{index}')}",
                    "summary": item["summary"],
                    "acceptance_refs": [item["ref"]],
                }
            )

    consumed_events = [
        {
            "id": event_id,
            "name": event_id,
            "source_contract_ref": event_id,
            "trigger": "Backend async update.",
            "ui_impact": "Refresh or reconcile visible page state.",
        }
        for event_id in contract_ids["event"]
    ]
    payload = {
        "version": "1.0",
        "feature_id": feature_id,
        "feature_name": feature_name,
        "platform": load_json(args.repo_context_snapshot).get("repo_context", {}).get("platform", "web"),
        "basis": [args.final_prd, args.frontend_scope] + ([args.api_contract] if args.api_contract else []),
        "consumed_apis": consumed_apis,
        "consumed_events": consumed_events,
        "local_commands": [{"id": "ui_validate", "summary": "Run local validation before submit.", "acceptance_refs": [item["ref"] for item in acceptance]}],
        "async_states": [
            {
                "trigger": "submit_or_refresh",
                "pending_state": "loading",
                "success_state": "ready",
                "failure_state": "error",
                "refresh_behavior": "manual_or_background_refresh",
            }
        ],
        "ui_visible_errors": [
            {
                "code": "GENERIC_FAILURE",
                "category": "network_or_server",
                "user_message_strategy": "Show actionable toast or inline error.",
                "retryable": True,
                "blocking": False,
            }
        ],
        "fallback_contracts": fallback_contracts,
        "acceptance_mapping": [
            {
                "acceptance_ref": item["ref"],
                "ui_refs": [entry["id"] for entry in consumed_apis] or [entry["id"] for entry in fallback_contracts],
                "checks": ["integration_test", "manual_rule_check"] if any("accessibility" in line.lower() for line in requirements) else ["integration_test"],
            }
            for item in acceptance
        ],
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
