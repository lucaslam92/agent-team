#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-frontend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from frontend_design_lib import load_json, write_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify frontend design assets and emit design_check_report.json.")
    parser.add_argument("--frontend-scope", required=True)
    parser.add_argument("--knowbase-context", required=True)
    parser.add_argument("--contract-view", required=True)
    parser.add_argument("--page-map", required=True)
    parser.add_argument("--navigation-map", required=True)
    parser.add_argument("--ui-structure", required=True)
    parser.add_argument("--state-model", required=True)
    parser.add_argument("--component-spec", required=True)
    parser.add_argument("--interaction-spec", required=True)
    parser.add_argument("--data-binding-plan", required=True)
    parser.add_argument("--quality-plan", required=True)
    parser.add_argument("--risk-register", required=True)
    parser.add_argument("--frontend-task-graph", required=True)
    parser.add_argument("--output", required=True)
    return parser


def verifier_result(verifier_id: str, status: str, blocking: bool, findings: list[dict[str, str]], repair_actions: list[str]) -> dict[str, object]:
    return {"verifier_id": verifier_id, "status": status, "blocking": blocking, "findings": findings, "repair_actions": repair_actions}


def finding(finding_id: str, summary: str, severity: str) -> dict[str, str]:
    return {"id": finding_id, "summary": summary, "severity": severity}


def main() -> None:
    args = build_parser().parse_args()
    frontend_scope = load_json(args.frontend_scope)
    knowbase_context = load_json(args.knowbase_context)
    contract_view = load_json(args.contract_view)
    page_map = load_json(args.page_map)
    navigation_map = load_json(args.navigation_map)
    ui_structure = load_json(args.ui_structure)
    state_model = load_json(args.state_model)
    component_spec = load_json(args.component_spec)
    interaction_spec = load_json(args.interaction_spec)
    data_binding_plan = load_json(args.data_binding_plan)
    quality_plan = load_json(args.quality_plan)
    risk_register = load_json(args.risk_register)
    task_graph = load_json(args.frontend_task_graph)
    feature_id = frontend_scope.get("feature_id", "unknown_feature")

    verifier_results = []
    scope_findings = []
    if not frontend_scope.get("frontend_responsibilities"):
        scope_findings.append(finding("scope_missing_frontend", "Frontend responsibilities are missing.", "high"))
    verifier_results.append(verifier_result("frontend_prd_coverage_verifier", "failed" if scope_findings else "passed", bool(scope_findings), scope_findings, ["Regenerate frontend_scope.json from final_prd and repo context."] if scope_findings else []))

    contract_findings = []
    if not contract_view.get("consumed_apis") and not contract_view.get("fallback_contracts"):
        contract_findings.append(finding("contract_missing", "frontend_contract_view.json has neither consumed APIs nor fallback contracts.", "high"))
    verifier_results.append(verifier_result("frontend_contract_alignment_verifier", "failed" if contract_findings else "passed", bool(contract_findings), contract_findings, ["Regenerate frontend_contract_view.json with contract or fallback mapping."] if contract_findings else []))

    nav_findings = []
    if not page_map.get("pages") or not navigation_map.get("routes"):
        nav_findings.append(finding("navigation_incomplete", "page_map.json or navigation_map.json is incomplete.", "high"))
    verifier_results.append(verifier_result("frontend_navigation_integrity_verifier", "failed" if nav_findings else "passed", bool(nav_findings), nav_findings, ["Regenerate page_map.json and navigation_map.json."] if nav_findings else []))

    state_findings = []
    if not state_model.get("state_transitions"):
        state_findings.append(finding("state_missing_transitions", "state_model.json does not define state transitions.", "high"))
    verifier_results.append(verifier_result("frontend_state_model_verifier", "failed" if state_findings else "passed", bool(state_findings), state_findings, ["Add explicit state transitions for core UI states."] if state_findings else []))

    component_findings = []
    if not component_spec.get("components"):
        component_findings.append(finding("component_missing", "component_spec.json contains no components.", "medium"))
    verifier_results.append(verifier_result("frontend_component_reuse_verifier", "warning" if component_findings else "passed", False, component_findings, ["Add reusable component definitions before coding handoff."] if component_findings else []))

    stack_findings = []
    if not knowbase_context.get("technical_stack", {}).get("framework"):
        stack_findings.append(finding("stack_missing_framework", "technical_stack.framework is empty.", "medium"))
    verifier_results.append(verifier_result("frontend_stack_conformance_verifier", "warning" if stack_findings else "passed", False, stack_findings, ["Add frontend stack details into knowledge docs."] if stack_findings else []))

    operability_findings = []
    if not quality_plan.get("observability") or not interaction_spec.get("feedback") or not data_binding_plan.get("request_bindings") and contract_view.get("consumed_apis"):
        operability_findings.append(finding("frontend_operability_gap", "Frontend quality, feedback, or data binding plan is incomplete.", "high"))
    verifier_results.append(verifier_result("frontend_operability_verifier", "failed" if operability_findings else "passed", bool(operability_findings), operability_findings, ["Complete quality_plan, interaction_spec, and data_binding_plan."] if operability_findings else []))

    task_findings = []
    if not task_graph.get("tasks"):
        task_findings.append(finding("task_graph_empty", "frontend_task_graph.json contains no tasks.", "high"))
    verifier_results.append(verifier_result("frontend_task_executability_verifier", "failed" if task_findings else "passed", bool(task_findings), task_findings, ["Regenerate frontend_task_graph.json with coding-ready tasks."] if task_findings else []))

    open_issues = [issue for result in verifier_results for issue in result["findings"]] + [finding(risk["id"], risk["summary"], risk["severity"]) for risk in risk_register.get("risks", []) if risk.get("blocking")]
    gate_results = [
        {"gate_id": "scope_gate", "status": "failed" if scope_findings or knowbase_context.get("extraction_status") == "blocked" else "passed", "blocking_issues": [item["summary"] for item in scope_findings]},
        {"gate_id": "ux_contract_gate", "status": "failed" if contract_findings or nav_findings or state_findings else "passed", "blocking_issues": [item["summary"] for item in contract_findings + nav_findings + state_findings]},
        {"gate_id": "implementation_ready_gate", "status": "failed" if operability_findings or task_findings or any(risk.get("blocking") for risk in risk_register.get("risks", [])) else "passed", "blocking_issues": [item["summary"] for item in operability_findings + task_findings] + [risk["summary"] for risk in risk_register.get("risks", []) if risk.get("blocking")]},
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
        "summary": {"status": status, "blocking_issue_count": blocking_issue_count, "warning_count": warning_count},
        "verifier_results": verifier_results,
        "gate_results": gate_results,
        "open_issues": open_issues,
        "repair_actions": [action for result in verifier_results for action in result["repair_actions"]],
        "resume_from": "design.frontend.scope_alignment" if scope_findings else ("design.frontend.contract_alignment" if contract_findings else "design.frontend.quality_plan"),
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
