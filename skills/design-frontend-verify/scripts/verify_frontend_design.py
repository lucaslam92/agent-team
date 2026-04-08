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


def finding(finding_id: str, summary: str, severity: str) -> dict[str, str]:
    return {"id": finding_id, "summary": summary, "severity": severity}


def verifier_result(verifier_id: str, status: str, blocking: bool, findings: list[dict[str, str]], repair_actions: list[str]) -> dict[str, object]:
    return {"verifier_id": verifier_id, "status": status, "blocking": blocking, "findings": findings, "repair_actions": repair_actions}


def criterion_result(criterion: str, passed: bool, evidence: list[str]) -> dict[str, object]:
    return {"criterion": criterion, "status": "passed" if passed else "failed", "evidence": evidence}


def gate_result(gate_id: str, criteria_results: list[dict[str, object]], blocking_issues: list[str], analyzer_ref: str) -> dict[str, object]:
    return {
        "gate_id": gate_id,
        "status": "passed" if all(item["status"] == "passed" for item in criteria_results) else "failed",
        "blocking_issues": blocking_issues,
        "criteria_results": criteria_results,
        "analyzer_ref": analyzer_ref,
    }


def analyzer_result(analyzer_id: str, failure_type: str, reasons: list[str], repair_actions: list[str], resume_from: str) -> dict[str, object]:
    return {
        "analyzer_id": analyzer_id,
        "failure_type": failure_type,
        "reasons": reasons,
        "repair_actions": repair_actions,
        "resume_from": resume_from,
    }


def task_index(tasks: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(task["id"]): task for task in tasks if task.get("id")}


def detect_cycle(tasks: list[dict[str, object]]) -> bool:
    nodes = task_index(tasks)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visited:
            return False
        if node_id in visiting:
            return True
        visiting.add(node_id)
        node = nodes.get(node_id, {})
        for dep in node.get("depends_on", []):
            if dep in nodes and visit(str(dep)):
                return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    return any(visit(node_id) for node_id in nodes)


def build_frontend_verifiers(
    frontend_scope: dict[str, object],
    knowbase_context: dict[str, object],
    contract_view: dict[str, object],
    page_map: dict[str, object],
    navigation_map: dict[str, object],
    ui_structure: dict[str, object],
    state_model: dict[str, object],
    component_spec: dict[str, object],
    interaction_spec: dict[str, object],
    data_binding_plan: dict[str, object],
    quality_plan: dict[str, object],
    risk_register: dict[str, object],
    task_graph: dict[str, object],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    tasks = task_graph.get("tasks", [])
    categories = {task.get("category") for task in tasks}

    scope_findings = []
    if not frontend_scope.get("frontend_responsibilities"):
        scope_findings.append(finding("scope_missing_frontend", "Frontend responsibilities are missing.", "high"))
    if not frontend_scope.get("shared_contracts"):
        scope_findings.append(finding("scope_missing_shared_contracts", "Shared contracts are missing from frontend_scope.json.", "medium"))
    results.append(verifier_result("frontend_prd_coverage_verifier", "failed" if any(item["severity"] == "high" for item in scope_findings) else ("warning" if scope_findings else "passed"), any(item["severity"] == "high" for item in scope_findings), scope_findings, ["Regenerate frontend_scope.json from final_prd and repo context."] if scope_findings else []))

    contract_findings = []
    if not contract_view.get("consumed_apis") and not contract_view.get("fallback_contracts"):
        contract_findings.append(finding("contract_missing", "frontend_contract_view.json has neither consumed APIs nor fallback contracts.", "high"))
    results.append(verifier_result("frontend_contract_alignment_verifier", "failed" if contract_findings else "passed", bool(contract_findings), contract_findings, ["Regenerate frontend_contract_view.json with contract or fallback mapping."] if contract_findings else []))

    nav_findings = []
    if not page_map.get("pages"):
        nav_findings.append(finding("page_map_missing_pages", "page_map.json must include pages.", "high"))
    if not navigation_map.get("routes"):
        nav_findings.append(finding("navigation_missing_routes", "navigation_map.json must include routes.", "high"))
    if not ui_structure.get("page_sections"):
        nav_findings.append(finding("ui_structure_missing_sections", "ui_structure.json must include page_sections.", "medium"))
    results.append(verifier_result("frontend_navigation_integrity_verifier", "failed" if any(item["severity"] == "high" for item in nav_findings) else ("warning" if nav_findings else "passed"), any(item["severity"] == "high" for item in nav_findings), nav_findings, ["Regenerate page_map.json, navigation_map.json, and ui_structure.json."] if nav_findings else []))

    state_findings = []
    if not state_model.get("state_transitions"):
        state_findings.append(finding("state_missing_transitions", "state_model.json does not define state transitions.", "high"))
    if not state_model.get("view_state"):
        state_findings.append(finding("state_missing_view_state", "state_model.json should define view_state.", "medium"))
    results.append(verifier_result("frontend_state_model_verifier", "failed" if any(item["severity"] == "high" for item in state_findings) else ("warning" if state_findings else "passed"), any(item["severity"] == "high" for item in state_findings), state_findings, ["Add explicit state transitions and view state coverage."] if state_findings else []))

    component_findings = []
    if not component_spec.get("components"):
        component_findings.append(finding("component_missing", "component_spec.json contains no components.", "medium"))
    if any("reuse_level" not in item for item in component_spec.get("components", [])):
        component_findings.append(finding("component_missing_reuse_level", "Some components do not declare reuse_level.", "medium"))
    results.append(verifier_result("frontend_component_reuse_verifier", "warning" if component_findings else "passed", False, component_findings, ["Add reusable component definitions before coding handoff."] if component_findings else []))

    knowbase_findings = []
    extraction_status = knowbase_context.get("extraction_status")
    if extraction_status == "blocked":
        knowbase_findings.append(finding("knowbase_blocked", "knowbase_context extraction is blocked.", "high"))
    elif extraction_status == "degraded":
        knowbase_findings.append(finding("knowbase_degraded", "knowbase_context is degraded and has unresolved gaps.", "medium"))
    results.append(verifier_result("design_knowbase_alignment_verifier", "failed" if extraction_status == "blocked" else ("warning" if knowbase_findings else "passed"), extraction_status == "blocked", knowbase_findings, ["Resolve missing knowbase sources before final frontend approval."] if knowbase_findings else []))

    stack_findings = []
    stack = knowbase_context.get("technical_stack", {})
    if not stack.get("framework"):
        stack_findings.append(finding("stack_missing_framework", "technical_stack.framework is empty.", "medium"))
    if not stack.get("design_system"):
        stack_findings.append(finding("stack_missing_design_system", "technical_stack.design_system is empty.", "medium"))
    results.append(verifier_result("frontend_stack_conformance_verifier", "warning" if stack_findings else "passed", False, stack_findings, ["Add frontend stack details into knowledge docs."] if stack_findings else []))

    operability_findings = []
    if not quality_plan.get("observability"):
        operability_findings.append(finding("quality_missing_observability", "quality_plan.json must define observability.", "high"))
    if not interaction_spec.get("feedback"):
        operability_findings.append(finding("interaction_missing_feedback", "interaction_spec.json must define feedback behavior.", "high"))
    if contract_view.get("consumed_apis") and not data_binding_plan.get("request_bindings"):
        operability_findings.append(finding("binding_missing_requests", "data_binding_plan.json must define request_bindings for consumed APIs.", "high"))
    results.append(verifier_result("frontend_operability_verifier", "failed" if any(item["severity"] == "high" for item in operability_findings) else ("warning" if operability_findings else "passed"), any(item["severity"] == "high" for item in operability_findings), operability_findings, ["Complete quality_plan, interaction_spec, and data_binding_plan."] if operability_findings else []))

    task_exec_findings = []
    if not tasks:
        task_exec_findings.append(finding("task_graph_empty", "frontend_task_graph.json contains no tasks.", "high"))
    elif any(not task.get("done_when") for task in tasks):
        task_exec_findings.append(finding("task_graph_missing_done_when", "Some frontend tasks do not declare done_when.", "medium"))
    results.append(verifier_result("frontend_task_executability_verifier", "failed" if any(item["severity"] == "high" for item in task_exec_findings) else ("warning" if task_exec_findings else "passed"), any(item["severity"] == "high" for item in task_exec_findings), task_exec_findings, ["Regenerate frontend_task_graph.json with coding-ready tasks."] if task_exec_findings else []))

    contract_schema_findings = []
    required_contract_keys = {"version", "feature_id", "feature_name", "platform", "basis", "consumed_apis", "consumed_events", "local_commands", "async_states", "ui_visible_errors", "fallback_contracts", "acceptance_mapping"}
    missing_keys = sorted(required_contract_keys - set(contract_view.keys()))
    if missing_keys:
        contract_schema_findings.append(finding("contract_view_missing_keys", f"frontend_contract_view.json misses keys: {', '.join(missing_keys)}.", "high"))
    results.append(verifier_result("frontend_contract_view_schema_verifier", "failed" if contract_schema_findings else "passed", bool(contract_schema_findings), contract_schema_findings, ["Regenerate frontend_contract_view.json with the canonical schema draft."] if contract_schema_findings else []))

    fallback_findings = []
    if not contract_view.get("consumed_apis") and not contract_view.get("fallback_contracts"):
        fallback_findings.append(finding("contract_view_missing_fallback", "Frontend contract view must provide fallback_contracts when consumed_apis is empty.", "high"))
    results.append(verifier_result("frontend_contract_fallback_verifier", "failed" if fallback_findings else "passed", bool(fallback_findings), fallback_findings, ["Add fallback contracts when backend api_contract.yaml is unavailable."] if fallback_findings else []))

    ac_mapping_findings = []
    if not contract_view.get("acceptance_mapping"):
        ac_mapping_findings.append(finding("contract_view_missing_ac_mapping", "frontend_contract_view.json must include acceptance_mapping.", "high"))
    elif any(not item.get("checks") for item in contract_view.get("acceptance_mapping", [])):
        ac_mapping_findings.append(finding("contract_view_missing_checks", "Some acceptance_mapping entries do not declare checks.", "medium"))
    results.append(verifier_result("frontend_ac_mapping_verifier", "failed" if any(item["severity"] == "high" for item in ac_mapping_findings) else ("warning" if ac_mapping_findings else "passed"), any(item["severity"] == "high" for item in ac_mapping_findings), ac_mapping_findings, ["Add acceptance mapping and checks to frontend_contract_view.json."] if ac_mapping_findings else []))

    task_schema_findings = []
    required_task_keys = {"id", "title", "category", "module", "depends_on", "priority", "acceptance_refs", "goal", "done_when", "verification_hooks", "retryable", "blocking"}
    for task in tasks:
        missing_task_keys = sorted(key for key in required_task_keys if key not in task)
        if missing_task_keys:
            task_schema_findings.append(finding(f"task_missing_fields_{task.get('id', 'unknown')}", f"Task {task.get('id', 'unknown')} misses fields: {', '.join(missing_task_keys)}.", "high"))
    results.append(verifier_result("frontend_task_graph_schema_verifier", "failed" if task_schema_findings else "passed", bool(task_schema_findings), task_schema_findings, ["Regenerate frontend_task_graph.json with the canonical task schema."] if task_schema_findings else []))

    dag_findings = []
    indexed_tasks = task_index(tasks)
    for task in tasks:
        for dep in task.get("depends_on", []):
            if dep not in indexed_tasks:
                dag_findings.append(finding(f"task_missing_dependency_{task.get('id', 'unknown')}", f"Task {task.get('id', 'unknown')} depends on missing task {dep}.", "high"))
    if detect_cycle(tasks):
        dag_findings.append(finding("task_graph_cycle", "frontend_task_graph.json contains a dependency cycle.", "high"))
    results.append(verifier_result("frontend_task_graph_dag_verifier", "failed" if dag_findings else "passed", bool(dag_findings), dag_findings, ["Remove missing dependencies and break cycles in frontend_task_graph.json."] if dag_findings else []))

    granularity_findings = []
    for task in tasks:
        if not task.get("done_when"):
            granularity_findings.append(finding(f"task_done_when_{task.get('id', 'unknown')}", f"Task {task.get('id', 'unknown')} lacks done_when criteria.", "high"))
        if not task.get("verification_hooks"):
            granularity_findings.append(finding(f"task_hooks_{task.get('id', 'unknown')}", f"Task {task.get('id', 'unknown')} lacks verification_hooks.", "medium"))
    results.append(verifier_result("frontend_task_graph_granularity_verifier", "failed" if any(item["severity"] == "high" for item in granularity_findings) else ("warning" if granularity_findings else "passed"), any(item["severity"] == "high" for item in granularity_findings), granularity_findings, ["Add observable done_when criteria and verification hooks to frontend tasks."] if granularity_findings else []))

    coverage_findings = []
    if page_map.get("pages") and not {"page", "state", "test"}.issubset(categories):
        coverage_findings.append(finding("task_graph_missing_page_coverage", "Task graph must include page, state, and test categories for each page flow.", "high"))
    if contract_view.get("consumed_apis") and not ({"contract_adapter"} & categories or {"data_binding"} & categories):
        coverage_findings.append(finding("task_graph_missing_contract_adapter", "Task graph must include contract_adapter or data_binding tasks when frontend consumes APIs.", "high"))
    if component_spec.get("components") and "component" not in categories:
        coverage_findings.append(finding("task_graph_missing_component_coverage", "Task graph must include component tasks when component_spec declares components.", "medium"))
    results.append(verifier_result("frontend_task_graph_coverage_verifier", "failed" if any(item["severity"] == "high" for item in coverage_findings) else ("warning" if coverage_findings else "passed"), any(item["severity"] == "high" for item in coverage_findings), coverage_findings, ["Expand frontend_task_graph.json to cover pages, components, and contract consumption work."] if coverage_findings else []))

    return results


def verifier_lookup(results: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(result["verifier_id"]): result for result in results}


def gate_from_verifiers(lookup: dict[str, dict[str, object]], gate_id: str) -> dict[str, object]:
    if gate_id == "scope_gate":
        criteria = [
            criterion_result("frontend_scope_declared", lookup["frontend_prd_coverage_verifier"]["status"] != "failed", ["frontend_prd_coverage_verifier"]),
            criterion_result("knowbase_context_usable", lookup["design_knowbase_alignment_verifier"]["status"] != "failed", ["design_knowbase_alignment_verifier"]),
            criterion_result("stack_context_present", lookup["frontend_stack_conformance_verifier"]["status"] != "failed", ["frontend_stack_conformance_verifier"]),
        ]
        blocking = [issue["summary"] for verifier_id in ["frontend_prd_coverage_verifier", "design_knowbase_alignment_verifier"] for issue in lookup[verifier_id]["findings"] if issue["severity"] == "high"]
        return gate_result("scope_gate", criteria, blocking, "frontend_scope_analyzer")
    if gate_id == "ux_contract_gate":
        criteria = [
            criterion_result("contract_view_valid", lookup["frontend_contract_view_schema_verifier"]["status"] == "passed", ["frontend_contract_view_schema_verifier"]),
            criterion_result("fallback_or_contract_present", lookup["frontend_contract_fallback_verifier"]["status"] == "passed", ["frontend_contract_fallback_verifier"]),
            criterion_result("navigation_and_state_valid", lookup["frontend_navigation_integrity_verifier"]["status"] != "failed" and lookup["frontend_state_model_verifier"]["status"] != "failed", ["frontend_navigation_integrity_verifier", "frontend_state_model_verifier"]),
            criterion_result("acceptance_mapping_present", lookup["frontend_ac_mapping_verifier"]["status"] != "failed", ["frontend_ac_mapping_verifier"]),
        ]
        blocking = [issue["summary"] for verifier_id in ["frontend_contract_view_schema_verifier", "frontend_contract_fallback_verifier", "frontend_navigation_integrity_verifier", "frontend_state_model_verifier", "frontend_ac_mapping_verifier"] for issue in lookup[verifier_id]["findings"] if issue["severity"] == "high"]
        return gate_result("ux_contract_gate", criteria, blocking, "frontend_contract_analyzer")
    criteria = [
        criterion_result("operability_ready", lookup["frontend_operability_verifier"]["status"] != "failed", ["frontend_operability_verifier"]),
        criterion_result("task_graph_is_valid_dag", lookup["frontend_task_graph_schema_verifier"]["status"] == "passed" and lookup["frontend_task_graph_dag_verifier"]["status"] == "passed", ["frontend_task_graph_schema_verifier", "frontend_task_graph_dag_verifier"]),
        criterion_result("task_graph_covers_design", lookup["frontend_task_graph_coverage_verifier"]["status"] != "failed" and lookup["frontend_task_graph_granularity_verifier"]["status"] != "failed", ["frontend_task_graph_coverage_verifier", "frontend_task_graph_granularity_verifier"]),
        criterion_result("component_and_quality_design_ready", lookup["frontend_component_reuse_verifier"]["status"] != "failed", ["frontend_component_reuse_verifier"]),
    ]
    blocking = [issue["summary"] for verifier_id in ["frontend_operability_verifier", "frontend_task_graph_schema_verifier", "frontend_task_graph_dag_verifier", "frontend_task_graph_coverage_verifier", "frontend_task_graph_granularity_verifier"] for issue in lookup[verifier_id]["findings"] if issue["severity"] == "high"]
    return gate_result("implementation_ready_gate", criteria, blocking, "frontend_ready_gate_analyzer")


def analyzers_from_gates(gates: list[dict[str, object]]) -> list[dict[str, object]]:
    analyzers: list[dict[str, object]] = []
    for gate in gates:
        if gate["status"] == "passed":
            continue
        failed_criteria = [item for item in gate["criteria_results"] if item["status"] == "failed"]
        analyzers.append(
            analyzer_result(
                analyzer_id=str(gate["analyzer_ref"]),
                failure_type=str(gate["gate_id"]),
                reasons=[item["criterion"] for item in failed_criteria] + list(gate["blocking_issues"]),
                repair_actions=[f"Repair failed criterion: {item['criterion']}" for item in failed_criteria],
                resume_from={
                    "scope_gate": "design.frontend.scope_alignment",
                    "ux_contract_gate": "design.frontend.contract_alignment",
                    "implementation_ready_gate": "design.frontend.quality_plan",
                }[str(gate["gate_id"])],
            )
        )
    return analyzers


def choose_resume_from(analyzers: list[dict[str, object]]) -> str:
    if analyzers:
        return str(analyzers[0]["resume_from"])
    return "design.frontend.verify"


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

    verifier_results = build_frontend_verifiers(
        frontend_scope=frontend_scope,
        knowbase_context=knowbase_context,
        contract_view=contract_view,
        page_map=page_map,
        navigation_map=navigation_map,
        ui_structure=ui_structure,
        state_model=state_model,
        component_spec=component_spec,
        interaction_spec=interaction_spec,
        data_binding_plan=data_binding_plan,
        quality_plan=quality_plan,
        risk_register=risk_register,
        task_graph=task_graph,
    )
    lookup = verifier_lookup(verifier_results)
    gate_results = [
        gate_from_verifiers(lookup, "scope_gate"),
        gate_from_verifiers(lookup, "ux_contract_gate"),
        gate_from_verifiers(lookup, "implementation_ready_gate"),
    ]
    analyzer_results = analyzers_from_gates(gate_results)
    open_issues = [issue for result in verifier_results for issue in result["findings"]] + [finding(risk["id"], risk["summary"], risk["severity"]) for risk in risk_register.get("risks", []) if risk.get("blocking")]
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
        "analyzer_results": analyzer_results,
        "open_issues": open_issues,
        "repair_actions": [action for result in verifier_results for action in result["repair_actions"]] + [action for result in analyzer_results for action in result["repair_actions"]],
        "resume_from": choose_resume_from(analyzer_results),
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
