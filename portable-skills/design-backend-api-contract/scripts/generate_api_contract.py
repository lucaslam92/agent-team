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
    slugify,
    write_yaml,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate backend api_contract.yaml.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--repo-context-snapshot", required=True)
    parser.add_argument("--backend-scope", required=True)
    parser.add_argument("--knowbase-context", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    repo_context = load_repo_context_snapshot(args.repo_context_snapshot)
    scope = load_json(args.backend_scope)
    knowbase_context = load_json(args.knowbase_context)

    feature_id, feature_name = feature_identity(final_prd)
    service = str(repo_context.get("primary_service") or "backend-service")
    acceptance = acceptance_items(final_prd)
    requirements = requirement_lines(final_prd)

    apis = []
    for index, item in enumerate(acceptance[: max(1, len(acceptance))], start=1):
        api_id = f"api_{slugify(item['summary'], f'api_{index}')}"
        apis.append(
            {
                "id": api_id,
                "name": f"{feature_name} API {index}",
                "summary": item["summary"],
                "kind": "command",
                "protocol": "http",
                "method": "POST",
                "path": f"/api/{slugify(feature_id)}/{index}",
                "tags": [slugify(feature_name)],
                "ownership": service,
                "auth": {"mode": "required", "roles": ["user"]},
                "idempotency": {"required": True, "strategy": "header_or_business_key"},
                "request": {"type": "object", "required": ["payload"]},
                "response": {"type": "object", "required": ["success"]},
                "errors": [
                    {
                        "code": "BAD_REQUEST",
                        "category": "validation",
                        "http_status": 400,
                        "retryable": False,
                        "user_visible": True,
                        "description": "Request payload violates backend contract.",
                    }
                ],
                "side_effects": {
                    "writes": [f"{slugify(feature_name)}_state"],
                    "publishes": [],
                    "cache_updates": [],
                    "external_calls": [],
                },
                "state_effects": [f"mutates {feature_name} state"],
                "consistency": {
                    "mode": "request_scoped",
                    "boundary": service,
                    "client_expectation": "Returns the accepted state transition result.",
                },
                "observability": ["structured_logs", "request_metrics"],
                "dependencies": [dep.get("name", "") for dep in repo_context.get("dependencies", []) if dep.get("name")],
                "acceptance_refs": [item["ref"]],
                "test_requirements": ["contract_test", "integration_test"],
            }
        )

    events = []
    if any("event" in line.lower() or "async" in line.lower() for line in requirements):
        events.append(
            {
                "id": f"event_{slugify(feature_id)}_updated",
                "name": f"{feature_name} Updated",
                "topic": f"{slugify(feature_id)}.updated",
                "producer": service,
                "consumers": ["downstream-services"],
                "trigger": "Published after successful write-side transition.",
                "payload": {"type": "object"},
                "delivery": {"mode": "at_least_once"},
                "observability": ["event_delivery_metrics"],
                "acceptance_refs": [item["ref"] for item in acceptance],
                "test_requirements": ["contract_test"],
            }
        )

    jobs = []
    if any("retry" in line.lower() or "job" in line.lower() or "schedule" in line.lower() for line in requirements):
        jobs.append(
            {
                "id": f"job_{slugify(feature_id)}_reconcile",
                "name": f"{feature_name} Reconcile Job",
                "trigger": "manual_or_async_recovery",
                "schedule": "on-demand",
                "module": service,
                "input": {"type": "object"},
                "effects": ["retries failed transitions"],
                "failure_policy": "retry_with_alert",
                "observability": ["job_duration", "job_failures"],
                "acceptance_refs": [item["ref"] for item in acceptance],
            }
        )

    contract = {
        "version": "1.0",
        "feature_id": feature_id,
        "feature_name": feature_name,
        "service": service,
        "owners": [service],
        "status": "draft",
        "design_basis": [args.final_prd, args.backend_scope, args.knowbase_context],
        "global_conventions": [rule["summary"] for rule in knowbase_context.get("api_rules", [])[:6]],
        "apis": apis,
        "events": events,
        "jobs": jobs,
        "shared_types": [
            {"name": f"{feature_name}Request", "kind": "request", "schema": {"type": "object"}},
            {"name": f"{feature_name}Response", "kind": "response", "schema": {"type": "object"}},
        ],
        "verification_mapping": [
            {
                "acceptance_ref": item["ref"],
                "contract_refs": [api["id"] for api in apis] + [event["id"] for event in events] + [job["id"] for job in jobs],
                "checks": ["contract_test", "integration_test"],
            }
            for item in acceptance
        ],
    }
    write_yaml(args.output, contract)


if __name__ == "__main__":
    main()
