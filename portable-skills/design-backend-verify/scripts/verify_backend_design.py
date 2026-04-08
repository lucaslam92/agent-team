#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-backend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from backend_design_lib import load_json, top_level_yaml_keys, write_json  # noqa: E402


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


def finding(finding_id: str, summary: str, severity: str) -> dict[str, str]:
    return {"id": finding_id, "summary": summary, "severity": severity}


def verifier_result(verifier_id: str, status: str, blocking: bool, findings: list[dict[str, str]], repair_actions: list[str]) -> dict[str, object]:
    return {
        "verifier_id": verifier_id,
        "status": status,
        "blocking": blocking,
        "findings": findings,
        "repair_actions": repair_actions,
    }


def criterion_result(criterion: str, passed: bool, evidence: list[str]) -> dict[str, object]:
    return {
        "criterion": criterion,
        "status": "passed" if passed else "failed",
        "evidence": evidence,
    }


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


def scan_yaml_array_items(path: str | Path, section: str) -> list[dict[str, str]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    items: list[dict[str, str]] = []
    inside = False
    current: dict[str, str] | None = None
    section_pattern = re.compile(rf"^{re.escape(section)}:\s*$")
    top_level_pattern = re.compile(r"^[A-Za-z0-9_]+:\s*$")
    key_value_pattern = re.compile(r"^([A-Za-z0-9_]+):\s*(.*)$")
    for line in lines:
        if section_pattern.match(line):
            inside = True
            current = None
            continue
        if not inside:
            continue
        if top_level_pattern.match(line) and not line.startswith(" "):
            break
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 2 and stripped == "-":
            if current is not None:
                items.append(current)
            current = {}
            continue
        if indent == 2 and stripped.startswith("- "):
            if current is not None:
                items.append(current)
            current = {}
            remainder = stripped[2:]
            match = key_value_pattern.match(remainder)
            if match:
                current[match.group(1)] = match.group(2)
            continue
        if current is not None and indent == 4:
            match = key_value_pattern.match(stripped)
            if match:
                current[match.group(1)] = match.group(2)
    if inside and current is not None:
        items.append(current)
    return items


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


def collect_open_issues(verifier_results: list[dict[str, object]], risk_register: dict[str, object]) -> list[dict[str, str]]:
    issues = [issue for result in verifier_results for issue in result["findings"]]
    issues.extend(
        finding(risk["id"], risk["summary"], risk["severity"])
        for risk in risk_register.get("risks", [])
        if risk.get("blocking")
    )
    return issues


def build_backend_verifiers(
    backend_scope: dict[str, object],
    knowbase_context: dict[str, object],
    api_contract_path: str,
    domain_model: dict[str, object],
    flow_model: dict[str, object],
    storage_plan: dict[str, object],
    quality_plan: dict[str, object],
    risk_register: dict[str, object],
    task_graph: dict[str, object],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    contract_keys = set(top_level_yaml_keys(api_contract_path))
    api_items = scan_yaml_array_items(api_contract_path, "apis")
    event_items = scan_yaml_array_items(api_contract_path, "events")
    job_items = scan_yaml_array_items(api_contract_path, "jobs")
    mapping_items = scan_yaml_array_items(api_contract_path, "verification_mapping")
    tasks = task_graph.get("tasks", [])
    categories = {task.get("category") for task in tasks}

    scope_findings = []
    if not backend_scope.get("backend_responsibilities"):
        scope_findings.append(finding("scope_missing_backend", "Backend responsibilities are missing.", "high"))
    if not backend_scope.get("shared_contracts"):
        scope_findings.append(finding("scope_missing_shared_contracts", "Shared contracts are missing from backend_scope.json.", "medium"))
    results.append(verifier_result("backend_prd_coverage_verifier", "failed" if any(item["severity"] == "high" for item in scope_findings) else ("warning" if scope_findings else "passed"), any(item["severity"] == "high" for item in scope_findings), scope_findings, ["Regenerate backend_scope.json from final_prd and repo context."] if scope_findings else []))

    contract_findings = []
    if not flow_model.get("main_flows"):
        contract_findings.append(finding("flow_missing_main", "flow_model.json must include at least one main flow.", "high"))
    if not storage_plan.get("migration_plan"):
        contract_findings.append(finding("storage_missing_migration_plan", "storage_plan.json must define migration_plan.", "high"))
    if not quality_plan.get("consistency_strategy"):
        contract_findings.append(finding("quality_missing_consistency", "quality_plan.json must define consistency_strategy.", "high"))
    results.append(verifier_result("backend_contract_completeness_verifier", "failed" if any(item["severity"] == "high" for item in contract_findings) else ("warning" if contract_findings else "passed"), any(item["severity"] == "high" for item in contract_findings), contract_findings, ["Complete flow_model, storage_plan, and quality_plan baseline fields."] if contract_findings else []))

    domain_findings = []
    if not domain_model.get("entities"):
        domain_findings.append(finding("domain_missing_entities", "domain_model.json lacks entities.", "high"))
    if not domain_model.get("state_machines"):
        domain_findings.append(finding("domain_missing_state_machine", "domain_model.json lacks state machines.", "high"))
    if not domain_model.get("invariants"):
        domain_findings.append(finding("domain_missing_invariants", "domain_model.json lacks invariants.", "medium"))
    results.append(verifier_result("backend_domain_integrity_verifier", "failed" if any(item["severity"] == "high" for item in domain_findings) else ("warning" if domain_findings else "passed"), any(item["severity"] == "high" for item in domain_findings), domain_findings, ["Add entities, state machines, and invariants to domain_model.json."] if domain_findings else []))

    knowbase_findings = []
    extraction_status = knowbase_context.get("extraction_status")
    if extraction_status == "blocked":
        knowbase_findings.append(finding("knowbase_blocked", "knowbase_context extraction is blocked.", "high"))
    elif extraction_status == "degraded":
        knowbase_findings.append(finding("knowbase_degraded", "knowbase_context is degraded and has unresolved gaps.", "medium"))
    results.append(verifier_result("design_knowbase_alignment_verifier", "failed" if extraction_status == "blocked" else ("warning" if knowbase_findings else "passed"), extraction_status == "blocked", knowbase_findings, ["Resolve missing knowbase sources before final approval."] if knowbase_findings else []))

    stack_findings = []
    stack = knowbase_context.get("technical_stack", {})
    if not stack.get("language"):
        stack_findings.append(finding("stack_missing_language", "technical_stack.language is empty.", "medium"))
    if not stack.get("framework"):
        stack_findings.append(finding("stack_missing_framework", "technical_stack.framework is empty.", "medium"))
    results.append(verifier_result("design_stack_conformance_verifier", "warning" if stack_findings else "passed", False, stack_findings, ["Add stack facts into knowledge/architecture docs."] if stack_findings else []))

    operability_findings = []
    if not quality_plan.get("observability"):
        operability_findings.append(finding("operability_missing_observability", "quality_plan.json must define observability.", "high"))
    if not quality_plan.get("rollout_plan"):
        operability_findings.append(finding("operability_missing_rollout", "quality_plan.json must define rollout_plan.", "medium"))
    if not storage_plan.get("migration_plan"):
        operability_findings.append(finding("operability_missing_migration", "storage_plan.json must define migration_plan.", "high"))
    results.append(verifier_result("backend_operability_verifier", "failed" if any(item["severity"] == "high" for item in operability_findings) else ("warning" if operability_findings else "passed"), any(item["severity"] == "high" for item in operability_findings), operability_findings, ["Complete observability, rollout, rollback, and migration details."] if operability_findings else []))

    task_exec_findings = []
    if not tasks:
        task_exec_findings.append(finding("task_graph_empty", "backend_task_graph.json contains no tasks.", "high"))
    elif any(not task.get("done_when") for task in tasks):
        task_exec_findings.append(finding("task_graph_missing_done_when", "Some tasks do not declare done_when criteria.", "medium"))
    results.append(verifier_result("backend_task_executability_verifier", "failed" if any(item["severity"] == "high" for item in task_exec_findings) else ("warning" if task_exec_findings else "passed"), any(item["severity"] == "high" for item in task_exec_findings), task_exec_findings, ["Regenerate backend_task_graph.json with observable done_when conditions."] if task_exec_findings else []))

    api_schema_findings = []
    required_contract_keys = {"version", "feature_id", "service", "apis", "events", "jobs", "shared_types", "verification_mapping"}
    if not required_contract_keys.issubset(contract_keys):
        api_schema_findings.append(finding("contract_missing_top_level_keys", "api_contract.yaml is missing required top-level keys.", "high"))
    results.append(verifier_result("api_contract_schema_verifier", "failed" if api_schema_findings else "passed", bool(api_schema_findings), api_schema_findings, ["Regenerate api_contract.yaml with the canonical schema draft."] if api_schema_findings else []))

    api_completeness_findings = []
    required_api_keys = {"id", "name", "summary", "method", "path", "errors", "side_effects", "consistency", "acceptance_refs", "test_requirements"}
    for item in api_items:
        missing_keys = sorted(required_api_keys - set(item.keys()))
        if missing_keys:
            api_completeness_findings.append(finding(f"api_missing_fields_{item.get('id', 'unknown')}", f"API contract item {item.get('id', 'unknown')} misses fields: {', '.join(missing_keys)}.", "high"))
    results.append(verifier_result("api_contract_completeness_verifier", "failed" if api_completeness_findings else "passed", bool(api_completeness_findings), api_completeness_findings, ["Add the missing required fields to each API item."] if api_completeness_findings else []))

    api_rule_findings = []
    if knowbase_context.get("api_rules") and "global_conventions" not in contract_keys:
        api_rule_findings.append(finding("contract_missing_global_conventions", "api_contract.yaml should declare global_conventions when api_rules exist.", "medium"))
    for item in api_items:
        for required_field in ["auth", "idempotency"]:
            if required_field not in item:
                api_rule_findings.append(finding(f"api_missing_{required_field}_{item.get('id', 'unknown')}", f"API contract item {item.get('id', 'unknown')} misses {required_field}.", "high"))
    results.append(verifier_result("api_contract_rule_alignment_verifier", "failed" if any(item["severity"] == "high" for item in api_rule_findings) else ("warning" if api_rule_findings else "passed"), any(item["severity"] == "high" for item in api_rule_findings), api_rule_findings, ["Align api_contract.yaml with knowbase API rules and auth/idempotency requirements."] if api_rule_findings else []))

    ac_mapping_findings = []
    if not mapping_items:
        ac_mapping_findings.append(finding("contract_missing_verification_mapping", "api_contract.yaml must include verification_mapping entries.", "high"))
    if any("acceptance_refs" not in item for item in api_items + event_items + job_items):
        ac_mapping_findings.append(finding("contract_missing_acceptance_refs", "Some contract items do not declare acceptance_refs.", "high"))
    results.append(verifier_result("api_contract_ac_mapping_verifier", "failed" if ac_mapping_findings else "passed", bool(ac_mapping_findings), ac_mapping_findings, ["Add acceptance_refs and verification_mapping coverage to the contract."] if ac_mapping_findings else []))

    testability_findings = []
    if any("test_requirements" not in item for item in api_items + event_items):
        testability_findings.append(finding("contract_missing_test_requirements", "Some API or event items do not declare test_requirements.", "high"))
    results.append(verifier_result("api_contract_testability_verifier", "failed" if testability_findings else "passed", bool(testability_findings), testability_findings, ["Add test_requirements to every API and event contract item."] if testability_findings else []))

    task_schema_findings = []
    required_task_keys = {"id", "title", "category", "module", "depends_on", "priority", "acceptance_refs", "goal", "done_when", "verification_hooks", "retryable", "blocking"}
    for task in tasks:
        missing_keys = sorted(key for key in required_task_keys if key not in task)
        if missing_keys:
            task_schema_findings.append(finding(f"task_missing_fields_{task.get('id', 'unknown')}", f"Task {task.get('id', 'unknown')} misses fields: {', '.join(missing_keys)}.", "high"))
    results.append(verifier_result("task_graph_schema_verifier", "failed" if task_schema_findings else "passed", bool(task_schema_findings), task_schema_findings, ["Regenerate backend_task_graph.json with the canonical task schema."] if task_schema_findings else []))

    dag_findings = []
    indexed_tasks = task_index(tasks)
    for task in tasks:
      for dep in task.get("depends_on", []):
          if dep not in indexed_tasks:
              dag_findings.append(finding(f"task_missing_dependency_{task.get('id', 'unknown')}", f"Task {task.get('id', 'unknown')} depends on missing task {dep}.", "high"))
    if detect_cycle(tasks):
        dag_findings.append(finding("task_graph_cycle", "backend_task_graph.json contains a dependency cycle.", "high"))
    results.append(verifier_result("task_graph_dag_verifier", "failed" if dag_findings else "passed", bool(dag_findings), dag_findings, ["Remove missing dependencies and break cycles in backend_task_graph.json."] if dag_findings else []))

    granularity_findings = []
    for task in tasks:
        if len(task.get("done_when", [])) == 0:
            granularity_findings.append(finding(f"task_done_when_{task.get('id', 'unknown')}", f"Task {task.get('id', 'unknown')} lacks done_when criteria.", "high"))
        if len(task.get("verification_hooks", [])) == 0:
            granularity_findings.append(finding(f"task_verification_hooks_{task.get('id', 'unknown')}", f"Task {task.get('id', 'unknown')} lacks verification_hooks.", "medium"))
    results.append(verifier_result("task_graph_granularity_verifier", "failed" if any(item["severity"] == "high" for item in granularity_findings) else ("warning" if granularity_findings else "passed"), any(item["severity"] == "high" for item in granularity_findings), granularity_findings, ["Add observable done_when criteria and verification hooks to granular tasks."] if granularity_findings else []))

    coverage_findings = []
    if api_items and not {"api", "domain", "test"}.issubset(categories):
        coverage_findings.append(finding("task_graph_missing_api_coverage", "Task graph must include api, domain, and test categories for API contract coverage.", "high"))
    if event_items and "event" not in categories:
        coverage_findings.append(finding("task_graph_missing_event_coverage", "Task graph must include event tasks when contract declares events.", "high"))
    if job_items and "job" not in categories:
        coverage_findings.append(finding("task_graph_missing_job_coverage", "Task graph must include job tasks when contract declares jobs.", "high"))
    results.append(verifier_result("task_graph_coverage_verifier", "failed" if coverage_findings else "passed", bool(coverage_findings), coverage_findings, ["Expand backend_task_graph.json to cover API, event, and job contract items."] if coverage_findings else []))

    return results


def verifier_lookup(results: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(result["verifier_id"]): result for result in results}


def gate_from_verifiers(lookup: dict[str, dict[str, object]], gate_id: str) -> dict[str, object]:
    if gate_id == "scope_gate":
        criteria = [
            criterion_result("backend_scope_declared", lookup["backend_prd_coverage_verifier"]["status"] != "failed", ["backend_prd_coverage_verifier"]),
            criterion_result("knowbase_context_usable", lookup["design_knowbase_alignment_verifier"]["status"] != "failed", ["design_knowbase_alignment_verifier"]),
            criterion_result("stack_context_present", lookup["design_stack_conformance_verifier"]["status"] != "failed", ["design_stack_conformance_verifier"]),
        ]
        blocking = [issue["summary"] for verifier_id in ["backend_prd_coverage_verifier", "design_knowbase_alignment_verifier"] for issue in lookup[verifier_id]["findings"] if issue["severity"] == "high"]
        return gate_result("scope_gate", criteria, blocking, "backend_scope_analyzer")
    if gate_id == "contract_gate":
        criteria = [
            criterion_result("api_contract_schema_valid", lookup["api_contract_schema_verifier"]["status"] == "passed", ["api_contract_schema_verifier"]),
            criterion_result("api_contract_complete", lookup["api_contract_completeness_verifier"]["status"] == "passed", ["api_contract_completeness_verifier"]),
            criterion_result("domain_and_flow_integrity", lookup["backend_domain_integrity_verifier"]["status"] != "failed" and lookup["backend_contract_completeness_verifier"]["status"] != "failed", ["backend_domain_integrity_verifier", "backend_contract_completeness_verifier"]),
            criterion_result("acceptance_mapping_present", lookup["api_contract_ac_mapping_verifier"]["status"] == "passed", ["api_contract_ac_mapping_verifier"]),
        ]
        blocking = [issue["summary"] for verifier_id in ["api_contract_schema_verifier", "api_contract_completeness_verifier", "backend_domain_integrity_verifier", "backend_contract_completeness_verifier", "api_contract_ac_mapping_verifier"] for issue in lookup[verifier_id]["findings"] if issue["severity"] == "high"]
        return gate_result("contract_gate", criteria, blocking, "backend_contract_analyzer")
    criteria = [
        criterion_result("operability_ready", lookup["backend_operability_verifier"]["status"] != "failed", ["backend_operability_verifier"]),
        criterion_result("task_graph_is_valid_dag", lookup["task_graph_schema_verifier"]["status"] == "passed" and lookup["task_graph_dag_verifier"]["status"] == "passed", ["task_graph_schema_verifier", "task_graph_dag_verifier"]),
        criterion_result("task_graph_covers_contract", lookup["task_graph_coverage_verifier"]["status"] == "passed" and lookup["task_graph_granularity_verifier"]["status"] != "failed", ["task_graph_coverage_verifier", "task_graph_granularity_verifier"]),
        criterion_result("contract_is_testable", lookup["api_contract_testability_verifier"]["status"] == "passed", ["api_contract_testability_verifier"]),
        criterion_result("no_blocking_risks", True, ["risk_register"]),
    ]
    blocking = [issue["summary"] for verifier_id in ["backend_operability_verifier", "task_graph_schema_verifier", "task_graph_dag_verifier", "task_graph_coverage_verifier", "task_graph_granularity_verifier", "api_contract_testability_verifier"] for issue in lookup[verifier_id]["findings"] if issue["severity"] == "high"]
    return gate_result("implementation_ready_gate", criteria, blocking, "backend_ready_gate_analyzer")


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
                    "scope_gate": "design.backend.scope_alignment",
                    "contract_gate": "design.backend.api_contract",
                    "implementation_ready_gate": "design.backend.quality_plan",
                }[str(gate["gate_id"])],
            )
        )
    return analyzers


def choose_resume_from(analyzers: list[dict[str, object]]) -> str:
    if analyzers:
        return str(analyzers[0]["resume_from"])
    return "design.backend.verify"


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
    feature_id = backend_scope.get("feature_id", "unknown_feature")

    verifier_results = build_backend_verifiers(
        backend_scope=backend_scope,
        knowbase_context=knowbase_context,
        api_contract_path=args.api_contract,
        domain_model=domain_model,
        flow_model=flow_model,
        storage_plan=storage_plan,
        quality_plan=quality_plan,
        risk_register=risk_register,
        task_graph=task_graph,
    )
    lookup = verifier_lookup(verifier_results)
    gate_results = [
        gate_from_verifiers(lookup, "scope_gate"),
        gate_from_verifiers(lookup, "contract_gate"),
        gate_from_verifiers(lookup, "implementation_ready_gate"),
    ]
    analyzer_results = analyzers_from_gates(gate_results)
    open_issues = collect_open_issues(verifier_results, risk_register)
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
        "analyzer_results": analyzer_results,
        "open_issues": open_issues,
        "repair_actions": [action for result in verifier_results for action in result["repair_actions"]] + [action for result in analyzer_results for action in result["repair_actions"]],
        "resume_from": choose_resume_from(analyzer_results),
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
