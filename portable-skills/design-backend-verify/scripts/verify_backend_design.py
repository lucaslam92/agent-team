#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shlex
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


def repair_plan_step(
    step_id: str,
    summary: str,
    skill: str,
    target_artifacts: list[str],
    rationale: str,
    auto_fixable: bool,
    command: str,
) -> dict[str, object]:
    return {
        "step_id": step_id,
        "summary": summary,
        "skill": skill,
        "target_artifacts": target_artifacts,
        "rationale": rationale,
        "auto_fixable": auto_fixable,
        "command": command,
    }


def analyzer_result(
    analyzer_id: str,
    failure_type: str,
    reasons: list[str],
    repair_actions: list[str],
    resume_from: str,
    suggested_skill: str,
    suggested_command: str,
    target_artifacts: list[str],
    auto_fixable: bool,
    repair_plan: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "analyzer_id": analyzer_id,
        "failure_type": failure_type,
        "reasons": reasons,
        "repair_actions": repair_actions,
        "resume_from": resume_from,
        "suggested_skill": suggested_skill,
        "suggested_command": suggested_command,
        "target_artifacts": target_artifacts,
        "auto_fixable": auto_fixable,
        "repair_plan": repair_plan,
    }


def unique_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


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


def blocking_risks(risk_register: dict[str, object]) -> list[dict[str, object]]:
    return [risk for risk in risk_register.get("risks", []) if risk.get("blocking")]


def shell(parts: list[str | Path]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def backend_command_context(backend_scope_path: str) -> dict[str, str]:
    design_dir = Path(backend_scope_path).resolve().parent
    if design_dir.name == "backend" and design_dir.parent.name == "design" and design_dir.parent.parent.name == "artifacts":
        workspace_root = design_dir.parents[2]
    else:
        workspace_root = Path.cwd()
    return {
        "workspace_root": str(workspace_root),
        "final_prd": str(workspace_root / "artifacts" / "prd" / "final_prd.json"),
        "knowledge_root": str(workspace_root / "knowledge"),
        "repo_overlay_root": str(workspace_root / "knowledge"),
        "repo_context_snapshot": str(design_dir / "repo_context_snapshot.json"),
        "backend_scope": str(design_dir / "backend_scope.json"),
        "knowbase_context": str(design_dir / "knowbase_context.json"),
        "api_contract": str(design_dir / "api_contract.yaml"),
        "domain_model": str(design_dir / "domain_model.json"),
        "flow_model": str(design_dir / "flow_model.json"),
        "storage_plan": str(design_dir / "storage_plan.json"),
        "quality_plan": str(design_dir / "quality_plan.json"),
        "risk_register": str(design_dir / "risk_register.json"),
        "backend_design_doc": str(design_dir / "backend_design.md"),
        "backend_task_graph": str(design_dir / "backend_task_graph.json"),
        "context_snapshot": str(design_dir / "design_context_snapshot.json"),
    }


def backend_skill_command(skill: str, ctx: dict[str, str]) -> str:
    command_map = {
        "design.backend.read_knowbase_context": [
            "python",
            "skills/design-backend-read-knowbase-context/scripts/read_knowbase_context.py",
            "--final-prd",
            ctx["final_prd"],
            "--knowledge-root",
            ctx["knowledge_root"],
            "--repo-overlay-root",
            ctx["repo_overlay_root"],
            "--output",
            ctx["knowbase_context"],
        ],
        "design.backend.scope_alignment": [
            "python",
            "skills/design-backend-scope-alignment/scripts/generate_scope.py",
            "--final-prd",
            ctx["final_prd"],
            "--repo-context-snapshot",
            ctx["repo_context_snapshot"],
            "--knowbase-context",
            ctx["knowbase_context"],
            "--output",
            ctx["backend_scope"],
        ],
        "design.backend.api_contract": [
            "python",
            "skills/design-backend-api-contract/scripts/generate_api_contract.py",
            "--final-prd",
            ctx["final_prd"],
            "--repo-context-snapshot",
            ctx["repo_context_snapshot"],
            "--backend-scope",
            ctx["backend_scope"],
            "--knowbase-context",
            ctx["knowbase_context"],
            "--output",
            ctx["api_contract"],
        ],
        "design.backend.domain_model": [
            "python",
            "skills/design-backend-domain-model/scripts/generate_domain_model.py",
            "--final-prd",
            ctx["final_prd"],
            "--backend-scope",
            ctx["backend_scope"],
            "--output",
            ctx["domain_model"],
        ],
        "design.backend.flow_model": [
            "python",
            "skills/design-backend-flow-model/scripts/generate_flow_model.py",
            "--final-prd",
            ctx["final_prd"],
            "--api-contract",
            ctx["api_contract"],
            "--output",
            ctx["flow_model"],
        ],
        "design.backend.storage_plan": [
            "python",
            "skills/design-backend-storage-plan/scripts/generate_storage_plan.py",
            "--final-prd",
            ctx["final_prd"],
            "--repo-context-snapshot",
            ctx["repo_context_snapshot"],
            "--knowbase-context",
            ctx["knowbase_context"],
            "--domain-model",
            ctx["domain_model"],
            "--flow-model",
            ctx["flow_model"],
            "--output",
            ctx["storage_plan"],
        ],
        "design.backend.quality_plan": [
            "python",
            "skills/design-backend-quality-plan/scripts/generate_quality_plan.py",
            "--final-prd",
            ctx["final_prd"],
            "--knowbase-context",
            ctx["knowbase_context"],
            "--quality-output",
            ctx["quality_plan"],
            "--risk-output",
            ctx["risk_register"],
        ],
        "design.backend.compile_doc": [
            "python",
            "skills/design-backend-compile-doc/scripts/compile_backend_design.py",
            "--final-prd",
            ctx["final_prd"],
            "--repo-context-snapshot",
            ctx["repo_context_snapshot"],
            "--knowbase-context",
            ctx["knowbase_context"],
            "--backend-scope",
            ctx["backend_scope"],
            "--api-contract",
            ctx["api_contract"],
            "--domain-model",
            ctx["domain_model"],
            "--flow-model",
            ctx["flow_model"],
            "--storage-plan",
            ctx["storage_plan"],
            "--quality-plan",
            ctx["quality_plan"],
            "--risk-register",
            ctx["risk_register"],
            "--doc-output",
            ctx["backend_design_doc"],
            "--task-graph-output",
            ctx["backend_task_graph"],
            "--context-snapshot-output",
            ctx["context_snapshot"],
        ],
    }
    return shell(command_map[skill])


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


def gate_from_verifiers(lookup: dict[str, dict[str, object]], gate_id: str, risk_register: dict[str, object]) -> dict[str, object]:
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
    blocking_risk_findings = [str(risk.get("summary", "Blocking risk")) for risk in blocking_risks(risk_register)]
    criteria = [
        criterion_result("operability_ready", lookup["backend_operability_verifier"]["status"] != "failed", ["backend_operability_verifier"]),
        criterion_result("task_graph_is_valid_dag", lookup["task_graph_schema_verifier"]["status"] == "passed" and lookup["task_graph_dag_verifier"]["status"] == "passed", ["task_graph_schema_verifier", "task_graph_dag_verifier"]),
        criterion_result("task_graph_covers_contract", lookup["task_graph_coverage_verifier"]["status"] == "passed" and lookup["task_graph_granularity_verifier"]["status"] != "failed", ["task_graph_coverage_verifier", "task_graph_granularity_verifier"]),
        criterion_result("contract_is_testable", lookup["api_contract_testability_verifier"]["status"] == "passed", ["api_contract_testability_verifier"]),
        criterion_result("no_blocking_risks", not blocking_risk_findings, ["risk_register"]),
    ]
    blocking = [issue["summary"] for verifier_id in ["backend_operability_verifier", "task_graph_schema_verifier", "task_graph_dag_verifier", "task_graph_coverage_verifier", "task_graph_granularity_verifier", "api_contract_testability_verifier"] for issue in lookup[verifier_id]["findings"] if issue["severity"] == "high"] + blocking_risk_findings
    return gate_result("implementation_ready_gate", criteria, blocking, "backend_ready_gate_analyzer")


def backend_repair_blueprint(gate_id: str, failed_criteria: list[dict[str, object]], ctx: dict[str, str]) -> dict[str, object]:
    failed = {str(item["criterion"]) for item in failed_criteria}

    if gate_id == "scope_gate":
        steps: list[dict[str, object]] = []
        if "knowbase_context_usable" in failed:
            steps.append(
                repair_plan_step(
                    "refresh_knowbase_context",
                    "Rebuild knowbase_context.json from the resolved knowledge sources.",
                    "design.backend.read_knowbase_context",
                    ["knowbase_context.json"],
                    "Downstream backend design skills should consume a single validated knowbase context instead of re-reading raw knowledge sources.",
                    True,
                    backend_skill_command("design.backend.read_knowbase_context", ctx),
                )
            )
        if "backend_scope_declared" in failed or "stack_context_present" in failed:
            steps.append(
                repair_plan_step(
                    "realign_backend_scope",
                    "Regenerate backend_scope.json with backend responsibilities, shared contracts, and stack-aware boundaries.",
                    "design.backend.scope_alignment",
                    ["backend_scope.json"],
                    "Scope alignment is the earliest backend artifact that captures responsibility boundaries and stack constraints.",
                    True,
                    backend_skill_command("design.backend.scope_alignment", ctx),
                )
            )
        if not steps:
            steps.append(
                repair_plan_step(
                    "rerun_scope_alignment",
                    "Rerun backend scope alignment to refresh the scope gate inputs.",
                    "design.backend.scope_alignment",
                    ["backend_scope.json"],
                    "The scope gate failed without a more specific criterion-level mapping.",
                    True,
                    backend_skill_command("design.backend.scope_alignment", ctx),
                )
            )
        return {
            "resume_from": steps[0]["skill"],
            "suggested_skill": steps[0]["skill"],
            "target_artifacts": unique_strings([artifact for step in steps for artifact in step["target_artifacts"]]),
            "auto_fixable": all(bool(step["auto_fixable"]) for step in steps),
            "repair_plan": steps,
        }

    if gate_id == "contract_gate":
        steps = []
        if {"api_contract_schema_valid", "api_contract_complete", "acceptance_mapping_present"} & failed:
            steps.append(
                repair_plan_step(
                    "repair_api_contract",
                    "Regenerate api_contract.yaml with canonical fields, acceptance_refs, and verification mapping.",
                    "design.backend.api_contract",
                    ["api_contract.yaml"],
                    "The contract gate depends on a canonical API contract before coding or verification can consume the backend design.",
                    True,
                    backend_skill_command("design.backend.api_contract", ctx),
                )
            )
        if "domain_and_flow_integrity" in failed:
            steps.extend(
                [
                    repair_plan_step(
                        "repair_domain_model",
                        "Rebuild domain_model.json with entities, state machines, and invariants.",
                        "design.backend.domain_model",
                        ["domain_model.json"],
                        "Domain gaps should be repaired in the dedicated domain model step instead of patched ad hoc later.",
                        True,
                        backend_skill_command("design.backend.domain_model", ctx),
                    ),
                    repair_plan_step(
                        "repair_flow_model",
                        "Regenerate flow_model.json to cover main flows, error flows, retry flows, and compensation flows.",
                        "design.backend.flow_model",
                        ["flow_model.json"],
                        "Flow completeness is a separate concern from the API contract and needs an explicit flow model refresh.",
                        True,
                        backend_skill_command("design.backend.flow_model", ctx),
                    ),
                    repair_plan_step(
                        "repair_storage_and_quality",
                        "Refresh storage_plan.json from the latest domain, flow, and knowbase context.",
                        "design.backend.storage_plan",
                        ["storage_plan.json"],
                        "Storage dependencies and migration gaps should be repaired in the dedicated storage planning step.",
                        True,
                        backend_skill_command("design.backend.storage_plan", ctx),
                    ),
                    repair_plan_step(
                        "repair_quality_plan",
                        "Refresh quality_plan.json and risk_register.json if consistency or operability assumptions changed.",
                        "design.backend.quality_plan",
                        ["quality_plan.json", "risk_register.json"],
                        "Consistency and rollout details belong in the backend quality planning step.",
                        True,
                        backend_skill_command("design.backend.quality_plan", ctx),
                    ),
                ]
            )
        if not steps:
            steps.append(
                repair_plan_step(
                    "rerun_contract_design",
                    "Rerun backend API contract generation to refresh contract gate inputs.",
                    "design.backend.api_contract",
                    ["api_contract.yaml"],
                    "The contract gate failed without a more specific mapping, so the contract step is the safest resume point.",
                    True,
                    backend_skill_command("design.backend.api_contract", ctx),
                )
            )
        return {
            "resume_from": steps[0]["skill"],
            "suggested_skill": steps[0]["skill"],
            "target_artifacts": unique_strings([artifact for step in steps for artifact in step["target_artifacts"]]),
            "auto_fixable": all(bool(step["auto_fixable"]) for step in steps),
            "repair_plan": steps,
        }

    steps = []
    if "operability_ready" in failed or "no_blocking_risks" in failed:
        steps.append(
            repair_plan_step(
                "repair_quality_and_risks",
                "Refresh quality_plan.json and risk_register.json with operability details, rollout, rollback, and explicit risk mitigation.",
                "design.backend.quality_plan",
                ["quality_plan.json", "risk_register.json"],
                "Implementation readiness cannot pass while operability details or blocking risks are unresolved.",
                False if "no_blocking_risks" in failed else True,
                backend_skill_command("design.backend.quality_plan", ctx),
            )
        )
    if "operability_ready" in failed:
        steps.append(
            repair_plan_step(
                "repair_storage_plan",
                "Refresh storage_plan.json if migration or dependency findings are part of the operability failure.",
                "design.backend.storage_plan",
                ["storage_plan.json"],
                "Operability issues often include storage and migration gaps that must be repaired before coding.",
                True,
                backend_skill_command("design.backend.storage_plan", ctx),
            )
        )
    if "contract_is_testable" in failed:
        steps.append(
            repair_plan_step(
                "repair_contract_testability",
                "Update api_contract.yaml so every API, event, and job declares test_requirements.",
                "design.backend.api_contract",
                ["api_contract.yaml"],
                "Verification and coding loops rely on explicit testability hooks in the backend contract.",
                True,
                backend_skill_command("design.backend.api_contract", ctx),
            )
        )
    if "task_graph_is_valid_dag" in failed or "task_graph_covers_contract" in failed:
        steps.append(
            repair_plan_step(
                "recompile_backend_task_graph",
                "Regenerate backend_task_graph.json and backend_design.md from the latest contract, models, and quality plan.",
                "design.backend.compile_doc",
                ["backend_task_graph.json", "backend_design.md", "design_context_snapshot.json"],
                "Task graph and compiled design issues should be repaired at the compile step so the bridge to Coding Mission stays consistent.",
                True,
                backend_skill_command("design.backend.compile_doc", ctx),
            )
        )
    if not steps:
        steps.append(
            repair_plan_step(
                "rerun_quality_plan",
                "Rerun backend quality planning to refresh implementation-readiness inputs.",
                "design.backend.quality_plan",
                ["quality_plan.json", "risk_register.json"],
                "The implementation-ready gate failed without a more specific mapping, so quality planning is the safest resume point.",
                True,
                backend_skill_command("design.backend.quality_plan", ctx),
            )
        )
    return {
        "resume_from": steps[0]["skill"],
        "suggested_skill": steps[0]["skill"],
        "target_artifacts": unique_strings([artifact for step in steps for artifact in step["target_artifacts"]]),
        "auto_fixable": all(bool(step["auto_fixable"]) for step in steps),
        "repair_plan": steps,
    }


def analyzers_from_gates(gates: list[dict[str, object]], ctx: dict[str, str]) -> list[dict[str, object]]:
    analyzers: list[dict[str, object]] = []
    for gate in gates:
        if gate["status"] == "passed":
            continue
        failed_criteria = [item for item in gate["criteria_results"] if item["status"] == "failed"]
        blueprint = backend_repair_blueprint(str(gate["gate_id"]), failed_criteria, ctx)
        analyzers.append(
            analyzer_result(
                analyzer_id=str(gate["analyzer_ref"]),
                failure_type=str(gate["gate_id"]),
                reasons=[item["criterion"] for item in failed_criteria] + list(gate["blocking_issues"]),
                repair_actions=[str(step["summary"]) for step in blueprint["repair_plan"]],
                resume_from=str(blueprint["resume_from"]),
                suggested_skill=str(blueprint["suggested_skill"]),
                suggested_command=str(blueprint["repair_plan"][0]["command"]),
                target_artifacts=list(blueprint["target_artifacts"]),
                auto_fixable=bool(blueprint["auto_fixable"]),
                repair_plan=list(blueprint["repair_plan"]),
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
    command_context = backend_command_context(args.backend_scope)
    gate_results = [
        gate_from_verifiers(lookup, "scope_gate", risk_register),
        gate_from_verifiers(lookup, "contract_gate", risk_register),
        gate_from_verifiers(lookup, "implementation_ready_gate", risk_register),
    ]
    analyzer_results = analyzers_from_gates(gate_results, command_context)
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
