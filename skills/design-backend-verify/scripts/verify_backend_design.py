#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-backend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from backend_design_lib import (  # noqa: E402
    load_json,
    top_level_yaml_keys,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify backend design assets and emit design_check_report.json.")
    parser.add_argument("--backend-scope", required=True)
    parser.add_argument("--knowbase-context", required=True)
    parser.add_argument("--api-contract", required=True)
    parser.add_argument("--domain-model", required=True)
    parser.add_argument("--flow-model", required=True)
    parser.add_argument("--storage-plan", required=True)
    parser.add_argument("--quality-plan", required=True)
    parser.add_argument("--risk-register", required=True)
    parser.add_argument("--backend-task-graph", required=True)
    parser.add_argument("--output", required=True)
    return parser


def verifier_result(verifier_id: str, status: str, blocking: bool, findings: list[dict[str, str]], repair_actions: list[str]) -> dict[str, object]:
    return {
        "verifier_id": verifier_id,
        "status": status,
        "blocking": blocking,
        "findings": findings,
        "repair_actions": repair_actions,
    }


def finding(finding_id: str, summary: str, severity: str) -> dict[str, str]:
    return {"id": finding_id, "summary": summary, "severity": severity}


def main() -> None:
    args = build_parser().parse_args()
    backend_scope = load_json(args.backend_scope)
    knowbase_context = load_json(args.knowbase_context)
    domain_model = load_json(args.domain_model)
    flow_model = load_json(args.flow_model)
    storage_plan = load_json(args.storage_plan)
    quality_plan = load_json(args.quality_plan)
    risk_register = load_json(args.risk_register)
    task_graph = load_json(args.backend_task_graph)
    contract_keys = top_level_yaml_keys(args.api_contract)

    feature_id = backend_scope.get("feature_id", "unknown_feature")
    verifier_results = []

    scope_findings = []
    if not backend_scope.get("backend_responsibilities"):
        scope_findings.append(finding("scope_missing_backend", "Backend responsibilities are missing.", "high"))
    verifier_results.append(
        verifier_result(
            "backend_prd_coverage_verifier",
            "failed" if scope_findings else "passed",
            bool(scope_findings),
            scope_findings,
            ["Regenerate backend_scope.json from final_prd and repo context."] if scope_findings else [],
        )
    )

    required_contract_keys = {"version", "feature_id", "service", "apis", "events", "jobs", "shared_types", "verification_mapping"}
    contract_findings = []
    if not required_contract_keys.issubset(set(contract_keys)):
        contract_findings.append(finding("contract_missing_keys", "api_contract.yaml is missing required top-level keys.", "high"))
    verifier_results.append(
        verifier_result(
            "backend_contract_completeness_verifier",
            "failed" if contract_findings else "passed",
            bool(contract_findings),
            contract_findings,
            ["Regenerate api_contract.yaml with the canonical schema draft."] if contract_findings else [],
        )
    )

    domain_findings = []
    if not domain_model.get("entities") or not domain_model.get("state_machines"):
        domain_findings.append(finding("domain_incomplete", "domain_model.json lacks entities or state machines.", "high"))
    verifier_results.append(
        verifier_result(
            "backend_domain_integrity_verifier",
            "failed" if domain_findings else "passed",
            bool(domain_findings),
            domain_findings,
            ["Add entities, aggregates, and state machine coverage."] if domain_findings else [],
        )
    )

    knowbase_findings = []
    if knowbase_context.get("extraction_status") == "blocked":
        knowbase_findings.append(finding("knowbase_blocked", "knowbase_context extraction is blocked.", "high"))
    elif knowbase_context.get("extraction_status") == "degraded":
        knowbase_findings.append(finding("knowbase_degraded", "knowbase_context is degraded and has unresolved gaps.", "medium"))
    verifier_results.append(
        verifier_result(
            "design_knowbase_alignment_verifier",
            "failed" if knowbase_context.get("extraction_status") == "blocked" else ("warning" if knowbase_findings else "passed"),
            knowbase_context.get("extraction_status") == "blocked",
            knowbase_findings,
            ["Resolve missing knowbase sources before final approval."] if knowbase_findings else [],
        )
    )

    stack_findings = []
    if not knowbase_context.get("technical_stack", {}).get("language"):
        stack_findings.append(finding("stack_missing_language", "technical_stack.language is empty.", "medium"))
    verifier_results.append(
        verifier_result(
            "design_stack_conformance_verifier",
            "warning" if stack_findings else "passed",
            False,
            stack_findings,
            ["Add stack facts into knowledge/architecture docs."] if stack_findings else [],
        )
    )

    operability_findings = []
    if not quality_plan.get("observability") or not storage_plan.get("migration_plan"):
        operability_findings.append(finding("operability_incomplete", "quality_plan or storage_plan is incomplete.", "high"))
    verifier_results.append(
        verifier_result(
            "backend_operability_verifier",
            "failed" if operability_findings else "passed",
            bool(operability_findings),
            operability_findings,
            ["Complete observability, rollout, rollback, and migration details."] if operability_findings else [],
        )
    )

    task_findings = []
    if not task_graph.get("tasks"):
        task_findings.append(finding("task_graph_empty", "backend_task_graph.json contains no tasks.", "high"))
    elif any(not task.get("done_when") for task in task_graph.get("tasks", [])):
        task_findings.append(finding("task_graph_done_when", "Some tasks do not declare done_when criteria.", "medium"))
    verifier_results.append(
        verifier_result(
            "backend_task_executability_verifier",
            "failed" if task_findings else "passed",
            bool(task_findings),
            task_findings,
            ["Regenerate backend_task_graph.json with observable done_when conditions."] if task_findings else [],
        )
    )

    open_issues = [
        issue
        for result in verifier_results
        for issue in result["findings"]
    ] + [
        finding(risk["id"], risk["summary"], risk["severity"])
        for risk in risk_register.get("risks", [])
        if risk.get("blocking")
    ]

    gate_results = [
        {
            "gate_id": "scope_gate",
            "status": "failed" if scope_findings or knowbase_context.get("extraction_status") == "blocked" else "passed",
            "blocking_issues": [item["summary"] for item in scope_findings + knowbase_findings if item["severity"] == "high"],
        },
        {
            "gate_id": "contract_gate",
            "status": "failed" if contract_findings or domain_findings else "passed",
            "blocking_issues": [item["summary"] for item in contract_findings + domain_findings],
        },
        {
            "gate_id": "implementation_ready_gate",
            "status": "failed" if operability_findings or task_findings or any(risk.get("blocking") for risk in risk_register.get("risks", [])) else "passed",
            "blocking_issues": [item["summary"] for item in operability_findings + task_findings] + [risk["summary"] for risk in risk_register.get("risks", []) if risk.get("blocking")],
        },
    ]

    blocking_issue_count = len([issue for issue in open_issues if issue["severity"] == "high"])
    warning_count = len([issue for issue in open_issues if issue["severity"] == "medium"])
    status = "passed"
    if any(gate["status"] == "failed" for gate in gate_results):
        status = "failed"
    elif warning_count:
        status = "degraded"

    payload = {
        "feature_id": feature_id,
        "summary": {
            "status": status,
            "blocking_issue_count": blocking_issue_count,
            "warning_count": warning_count,
        },
        "verifier_results": verifier_results,
        "gate_results": gate_results,
        "open_issues": open_issues,
        "repair_actions": [action for result in verifier_results for action in result["repair_actions"]],
        "resume_from": "design.backend.scope_alignment" if scope_findings else ("design.backend.api_contract" if contract_findings else "design.backend.quality_plan"),
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
