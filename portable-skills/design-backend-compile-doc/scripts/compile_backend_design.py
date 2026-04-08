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
    scan_contract_ids,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile backend design doc, task graph, and context snapshot.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--repo-context-snapshot", required=True)
    parser.add_argument("--knowbase-context", required=True)
    parser.add_argument("--backend-scope", required=True)
    parser.add_argument("--api-contract", required=True)
    parser.add_argument("--domain-model", required=True)
    parser.add_argument("--flow-model", required=True)
    parser.add_argument("--storage-plan", required=True)
    parser.add_argument("--quality-plan", required=True)
    parser.add_argument("--risk-register", required=True)
    parser.add_argument("--doc-output", required=True)
    parser.add_argument("--task-graph-output", required=True)
    parser.add_argument("--context-snapshot-output", required=True)
    return parser


def write_text(path: str | Path, content: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def build_task_graph(feature_id: str, service: str, contract_ids: dict[str, list[str]], storage_plan: dict[str, object], risk_register: dict[str, object]) -> dict[str, object]:
    tasks: list[dict[str, object]] = []
    for api_id in contract_ids["api"]:
        tasks.extend(
            [
                {
                    "id": f"{api_id}_domain",
                    "title": f"Implement domain logic for {api_id}",
                    "category": "domain",
                    "module": service,
                    "depends_on": [],
                    "parallel_group": "domain",
                    "priority": "high",
                    "from_contract": [api_id],
                    "from_design_artifacts": ["domain_model.json", "flow_model.json"],
                    "acceptance_refs": [],
                    "goal": "Deliver deterministic business state transition.",
                    "files_hint": [],
                    "implementation_notes": ["Follow backend_scope and knowbase rules."],
                    "done_when": ["Domain service handles happy path and validation path."],
                    "verification_hooks": ["compile", "unit_test"],
                    "retryable": False,
                    "blocking": True,
                },
                {
                    "id": f"{api_id}_api",
                    "title": f"Implement API boundary for {api_id}",
                    "category": "api",
                    "module": service,
                    "depends_on": [f"{api_id}_domain"],
                    "parallel_group": "api",
                    "priority": "high",
                    "from_contract": [api_id],
                    "from_design_artifacts": ["api_contract.yaml"],
                    "acceptance_refs": [],
                    "goal": "Expose backend contract safely.",
                    "files_hint": [],
                    "implementation_notes": ["Respect contract auth, idempotency, and error model."],
                    "done_when": ["Route/controller matches api_contract and delegates to domain layer."],
                    "verification_hooks": ["compile", "contract_test"],
                    "retryable": False,
                    "blocking": True,
                },
                {
                    "id": f"{api_id}_test",
                    "title": f"Cover {api_id} with tests",
                    "category": "test",
                    "module": service,
                    "depends_on": [f"{api_id}_api"],
                    "parallel_group": "test",
                    "priority": "high",
                    "from_contract": [api_id],
                    "from_design_artifacts": ["api_contract.yaml", "backend_task_graph.json"],
                    "acceptance_refs": [],
                    "goal": "Validate behavior against contract and acceptance mapping.",
                    "files_hint": [],
                    "implementation_notes": ["Cover happy path, validation errors, and integration seam."],
                    "done_when": ["Unit or contract tests assert request/response contract."],
                    "verification_hooks": ["unit_test", "contract_test"],
                    "retryable": True,
                    "blocking": False,
                },
            ]
        )
    if storage_plan.get("tables"):
        tasks.append(
            {
                "id": "storage_plan_apply",
                "title": "Implement storage and migration updates",
                "category": "storage",
                "module": service,
                "depends_on": [task["id"] for task in tasks if task["category"] == "domain"],
                "parallel_group": "storage",
                "priority": "high",
                "from_contract": [],
                "from_design_artifacts": ["storage_plan.json"],
                "acceptance_refs": [],
                "goal": "Add persistent storage support for the feature.",
                "files_hint": [],
                "implementation_notes": ["Create migrations before enabling new write paths."],
                "done_when": ["Required tables, indexes, and cache keys exist."],
                "verification_hooks": ["compile", "integration_test"],
                "retryable": False,
                "blocking": True,
            }
        )
    for event_id in contract_ids["event"]:
        tasks.append(
            {
                "id": f"{event_id}_event",
                "title": f"Implement event publication for {event_id}",
                "category": "event",
                "module": service,
                "depends_on": [task["id"] for task in tasks if task["category"] in {"api", "storage"}],
                "parallel_group": "event",
                "priority": "medium",
                "from_contract": [event_id],
                "from_design_artifacts": ["api_contract.yaml", "flow_model.json"],
                "acceptance_refs": [],
                "goal": "Publish backend event with expected delivery semantics.",
                "files_hint": [],
                "implementation_notes": ["Track publish success/failure and idempotent replay behavior."],
                "done_when": ["Event payload and producer logic match contract."],
                "verification_hooks": ["integration_test", "contract_test"],
                "retryable": True,
                "blocking": False,
            }
        )
    for job_id in contract_ids["job"]:
        tasks.append(
            {
                "id": f"{job_id}_job",
                "title": f"Implement recovery job for {job_id}",
                "category": "job",
                "module": service,
                "depends_on": [task["id"] for task in tasks if task["category"] in {"event", "storage"}],
                "parallel_group": "job",
                "priority": "medium",
                "from_contract": [job_id],
                "from_design_artifacts": ["api_contract.yaml", "quality_plan.json"],
                "acceptance_refs": [],
                "goal": "Deliver safe async recovery or reconciliation behavior.",
                "files_hint": [],
                "implementation_notes": ["Respect failure policy and observability requirements."],
                "done_when": ["Job trigger, retry policy, and failure alerts are implemented."],
                "verification_hooks": ["integration_test", "smoke_test"],
                "retryable": True,
                "blocking": False,
            }
        )
    tasks.append(
        {
            "id": "observability_setup",
            "title": "Add observability coverage",
            "category": "observability",
            "module": service,
            "depends_on": [task["id"] for task in tasks if task["category"] in {"api", "event", "job"}],
            "parallel_group": "observability",
            "priority": "medium",
            "from_contract": [],
            "from_design_artifacts": ["quality_plan.json"],
            "acceptance_refs": [],
            "goal": "Expose logs, metrics, and alerts for the new backend behavior.",
            "files_hint": [],
            "implementation_notes": ["Instrument request path, async path, and failures."],
            "done_when": ["Key metrics and structured logs are visible for the feature."],
            "verification_hooks": ["smoke_test", "manual_rule_check"],
            "retryable": True,
            "blocking": False,
        }
    )
    blocking_issues = [risk["summary"] for risk in risk_register.get("risks", []) if risk.get("blocking")]
    return {
        "version": "1.0",
        "feature_id": feature_id,
        "service": service,
        "generated_from": [
            "backend_scope.json",
            "api_contract.yaml",
            "domain_model.json",
            "flow_model.json",
            "storage_plan.json",
            "quality_plan.json",
            "risk_register.json",
        ],
        "execution_policy": {
            "default_parallelism": "module_safe_parallelism",
            "notes": ["Keep domain before API, and API/storage before event/job when coupled."],
        },
        "tasks": tasks,
        "checkpoints": [
            {"id": "cp_contract", "summary": "Contract and domain skeleton ready.", "task_ids": [task["id"] for task in tasks[:3]]},
            {"id": "cp_operability", "summary": "Storage, async, and observability ready.", "task_ids": [task["id"] for task in tasks[3:]]},
        ],
        "final_gate": {
            "ready": not blocking_issues and bool(tasks),
            "required_checks": ["compile", "contract_test", "integration_test"],
            "blocking_issues": blocking_issues,
            "notes": ["All blocking issues must be cleared before coding exit."],
        },
    }


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    repo_context = load_repo_context_snapshot(args.repo_context_snapshot)
    knowbase_context = load_json(args.knowbase_context)
    backend_scope = load_json(args.backend_scope)
    domain_model = load_json(args.domain_model)
    flow_model = load_json(args.flow_model)
    storage_plan = load_json(args.storage_plan)
    quality_plan = load_json(args.quality_plan)
    risk_register = load_json(args.risk_register)
    feature_id, feature_name = feature_identity(final_prd)
    service = str(repo_context.get("primary_service") or "backend-service")
    contract_ids = scan_contract_ids(args.api_contract)
    task_graph = build_task_graph(feature_id, service, contract_ids, storage_plan, risk_register)
    write_json(args.task_graph_output, task_graph)

    context_snapshot = {
        "feature_id": feature_id,
        "prd_source": args.final_prd,
        "repo_context_sources": load_json(args.repo_context_snapshot).get("repo_context_sources", [args.repo_context_snapshot]),
        "knowbase_sources": [ref["path"] for ref in knowbase_context.get("resolved_references", [])],
        "key_constraints": [note["summary"] for note in knowbase_context.get("architecture_constraints", [])[:6]] + [note["summary"] for note in knowbase_context.get("backend_rules", [])[:6]],
        "status": "degraded" if knowbase_context.get("extraction_status") == "degraded" else "ready",
    }
    write_json(args.context_snapshot_output, context_snapshot)

    acceptance_refs = [item["ref"] for item in acceptance_items(final_prd)]
    doc = f"""# Backend Design

## Overview
- Feature: {feature_name}
- Service: {service}
- Acceptance refs: {", ".join(acceptance_refs)}

## Design Basis
- final_prd: {args.final_prd}
- repo context: {args.repo_context_snapshot}
- knowbase context: {args.knowbase_context}

## Scope And Responsibilities
- Backend responsibilities: {len(backend_scope.get("backend_responsibilities", []))}
- Shared contracts: {len(backend_scope.get("shared_contracts", []))}

## API Contract Summary
- APIs: {len(contract_ids['api'])}
- Events: {len(contract_ids['event'])}
- Jobs: {len(contract_ids['job'])}

## Domain Model Summary
- Entities: {len(domain_model.get('entities', []))}
- State machines: {len(domain_model.get('state_machines', []))}

## Main Flows And Error Flows
- Main flows: {len(flow_model.get('main_flows', []))}
- Error flows: {len(flow_model.get('error_flows', []))}

## Storage And Dependencies
- Tables: {len(storage_plan.get('tables', []))}
- External dependencies: {len(storage_plan.get('external_dependencies', []))}

## Reliability And Quality Plan
- Idempotency: {quality_plan['idempotency_strategy']['summary']}
- Observability: {quality_plan['observability']['summary']}

## Risks And Deferred Items
- Risks: {len(risk_register.get('risks', []))}

## Coding Task Breakdown
- Tasks: {len(task_graph.get('tasks', []))}

## Verification Mapping
- Required checks: {", ".join(task_graph['final_gate']['required_checks'])}

## Open Issues
{chr(10).join(f"- {risk['summary']}" for risk in risk_register.get('risks', []) if risk.get('blocking')) or "- None"}
"""
    write_text(args.doc_output, doc)


if __name__ == "__main__":
    main()
