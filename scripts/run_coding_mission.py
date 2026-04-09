#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INPUT_KEYS = ["final_prd", "repo_context", "knowbase_context", "design_assets", "task_graph", "design_check_report"]
EVIDENCE_GROUPS = ["compile", "lint", "integration", "contract", "smoke"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coding Mission orchestrator: read_inputs -> select_task_batch -> verify -> compile_report")
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--output-dir", default="artifacts/coding")
    parser.add_argument("--max-tasks", type=int, default=10)
    parser.add_argument("--execute-hooks", action="store_true")
    parser.add_argument("--execute-evidence", action="store_true")
    return parser


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_input_contract(inputs: dict[str, Any]) -> list[str]:
    return [key for key in INPUT_KEYS if key not in inputs]


def passed_design_gate(report: dict[str, Any]) -> bool:
    return report.get("summary", {}).get("status") in {"passed", "degraded"}


def infer_endpoint(task: dict[str, Any]) -> str:
    endpoint = str(task.get("endpoint", "")).strip()
    if endpoint:
        return endpoint
    task_type = str(task.get("task_type", "")).lower()
    return "backend" if task_type in {"domain", "storage", "api", "event", "job"} else "frontend"


def select_ready_tasks(task_graph: dict[str, Any], max_tasks: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    tasks = task_graph.get("tasks", [])
    selected_checkpoint = str(task_graph.get("checkpoint", "default"))
    done_ids = {str(item.get("task_id")) for item in tasks if item.get("status") == "done"}
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for task in tasks:
        task_id = str(task.get("task_id", ""))
        if task.get("status") == "done":
            continue
        depends_on = [str(dep) for dep in task.get("depends_on", [])]
        missing_deps = [dep for dep in depends_on if dep not in done_ids]
        blocked = bool(task.get("blocked", False))
        assets_ready = bool(task.get("design_assets_ready", True))
        checkpoint_match = str(task.get("checkpoint", selected_checkpoint)) == selected_checkpoint
        has_design_refs = bool(task.get("design_artifact_refs", []))
        has_changed_files = bool(task.get("changed_files", []))
        if missing_deps or blocked or not assets_ready or not checkpoint_match or not has_design_refs or not has_changed_files:
            reason = []
            if missing_deps:
                reason.append("dependencies_not_satisfied")
                unresolved.append({"task_id": task_id, "missing_dependencies": missing_deps})
            if blocked:
                reason.append("blocking_issue")
            if not assets_ready:
                reason.append("design_assets_incomplete")
            if not checkpoint_match:
                reason.append("checkpoint_not_selected")
            if not has_design_refs:
                reason.append("design_refs_missing")
            if not has_changed_files:
                reason.append("changed_files_missing")
            skipped.append({"task_id": task_id, "reason": ",".join(reason), "depends_on": depends_on, "blocking": blocked})
            continue
        selected.append(task)
        if len(selected) >= max_tasks:
            break
    return selected, skipped, unresolved


def build_selected_task_batch(inputs: dict[str, Any], selected: list[dict[str, Any]], skipped: list[dict[str, Any]], unresolved: list[dict[str, Any]]) -> dict[str, Any]:
    task_graph = inputs.get("task_graph", {})
    selected_items: list[dict[str, Any]] = []
    selection_reasons: list[dict[str, Any]] = []
    execution_order: list[str] = []
    for task in selected:
        task_id = str(task.get("task_id"))
        execution_order.append(task_id)
        endpoint = infer_endpoint(task)
        selected_items.append(
            {
                "task_id": task_id,
                "task_type": task.get("task_type", "unknown"),
                "endpoint": endpoint,
                "stack_profile": task.get("stack_profile", "default"),
                "priority": task.get("priority", "medium"),
                "checkpoint": task.get("checkpoint", "default"),
                "blocking": bool(task.get("blocking", False)),
                "depends_on": task.get("depends_on", []),
                "done_when": task.get("done_when", []),
                "verification_hooks": task.get("verification_hooks", []),
                "design_artifact_refs": task.get("design_artifact_refs", []),
                "changed_files": task.get("changed_files", []),
            }
        )
        selection_reasons.append({"task_id": task_id, "reasons": ["ready_task", f"endpoint:{endpoint}", f"priority:{task.get('priority', 'medium')}"]})

    return {
        "feature_id": inputs.get("feature_id", "unknown_feature"),
        "platform": task_graph.get("platform", "cross"),
        "selection_timestamp": datetime.now(timezone.utc).isoformat(),
        "selected_checkpoint": task_graph.get("checkpoint", "default"),
        "selected_tasks": selected_items,
        "skipped_tasks": skipped,
        "selection_reasons": selection_reasons,
        "unresolved_dependencies": unresolved,
        "execution_order": execution_order,
    }


def run_task_hooks(selected_tasks: list[dict[str, Any]], execute_hooks: bool) -> list[dict[str, Any]]:
    results = []
    for task in selected_tasks:
        for hook in list(task.get("verification_hooks", [])):
            if not execute_hooks:
                results.append({"task_id": task.get("task_id"), "hook": hook, "status": "planned", "exit_code": None})
                continue
            completed = subprocess.run(str(hook), shell=True)
            results.append({"task_id": task.get("task_id"), "hook": hook, "status": "passed" if completed.returncode == 0 else "failed", "exit_code": completed.returncode})
    return results


def run_command_group(commands: list[str], execute: bool) -> list[dict[str, Any]]:
    results = []
    for command in commands:
        if not execute:
            results.append({"command": command, "status": "planned", "exit_code": None})
        else:
            completed = subprocess.run(command, shell=True)
            results.append({"command": command, "status": "passed" if completed.returncode == 0 else "failed", "exit_code": completed.returncode})
    return results


def profile_key_for_task(task: dict[str, Any]) -> str:
    return f"{task.get('endpoint', 'unknown')}::{task.get('stack_profile', 'default')}"


def get_profile_plan(verification_plan: dict[str, Any], profile_key: str) -> dict[str, list[str]]:
    profiles = verification_plan.get("endpoint_profiles", {})
    if profile_key in profiles and isinstance(profiles[profile_key], dict):
        return profiles[profile_key]
    return verification_plan


def build_execution_context(inputs: dict[str, Any], selected_batch: dict[str, Any]) -> dict[str, Any]:
    endpoint_profiles = sorted({f"{t.get('endpoint', 'unknown')}::{t.get('stack_profile', 'default')}" for t in selected_batch.get("selected_tasks", [])})
    return {
        "feature_id": inputs.get("feature_id", "unknown_feature"),
        "platform": selected_batch.get("platform", "cross"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_graph_sources": inputs.get("task_graph", {}).get("sources", []),
        "design_asset_refs": sorted(inputs.get("design_assets", {}).keys()),
        "repo_context_refs": sorted(inputs.get("repo_context", {}).keys()),
        "selected_checkpoint": selected_batch.get("selected_checkpoint", "default"),
        "endpoint_profiles": endpoint_profiles,
    }


def build_changed_files(selected_tasks: list[dict[str, Any]]) -> dict[str, Any]:
    files = []
    for task in selected_tasks:
        for path in task.get("changed_files", []):
            files.append(
                {
                    "path": path,
                    "task_refs": [task.get("task_id")],
                    "module": task.get("task_type", "unknown"),
                    "endpoint": task.get("endpoint", "unknown"),
                    "change_type": "modified",
                    "design_artifact_refs": task.get("design_artifact_refs", []),
                }
            )
    return {"files": files, "count": len(files)}


def build_task_execution_report(selected_tasks: list[dict[str, Any]], hook_results: list[dict[str, Any]]) -> dict[str, Any]:
    hooks_by_task: dict[str, list[dict[str, Any]]] = {}
    for hook in hook_results:
        hooks_by_task.setdefault(str(hook.get("task_id")), []).append(hook)
    tasks = []
    for task in selected_tasks:
        task_id = str(task.get("task_id"))
        task_hooks = hooks_by_task.get(task_id, [])
        failed = any(item.get("status") == "failed" for item in task_hooks)
        status = "failed" if failed else ("planned" if task_hooks and task_hooks[0].get("status") == "planned" else "completed")
        tasks.append({"task_id": task_id, "status": status, "changed_files": task.get("changed_files", []), "done_when_results": [{"condition": c, "status": "unknown"} for c in task.get("done_when", [])], "hook_results": task_hooks, "blockers": ["verification_hook_failed"] if failed else [], "notes": "generated by coding mission mvp"})
    return {"tasks": tasks, "task_count": len(tasks)}


def build_implementation_evidence(inputs: dict[str, Any], hook_results: list[dict[str, Any]], execute_evidence: bool) -> dict[str, Any]:
    plan = inputs.get("verification_plan", {})
    selected_tasks = list(inputs.get("_selected_tasks", []))
    profile_keys = sorted({profile_key_for_task(task) for task in selected_tasks})
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in EVIDENCE_GROUPS}
    profile_command_count: dict[str, int] = {}
    for key in profile_keys:
        profile_plan = get_profile_plan(plan, key)
        profile_command_count[key] = sum(len(list(profile_plan.get(group, []))) for group in EVIDENCE_GROUPS)
        for group in EVIDENCE_GROUPS:
            commands = [f"{cmd}" for cmd in list(profile_plan.get(group, []))]
            grouped[group].extend(run_command_group(commands, execute_evidence))

    return {
        "compile_results": grouped["compile"],
        "lint_results": grouped["lint"],
        "unit_test_results": hook_results,
        "integration_test_results": grouped["integration"],
        "contract_test_results": grouped["contract"],
        "smoke_results": grouped["smoke"],
        "summary": {
            "passed_hook_count": len([h for h in hook_results if h.get("status") == "passed"]),
            "failed_hook_count": len([h for h in hook_results if h.get("status") == "failed"]),
            "planned_hook_count": len([h for h in hook_results if h.get("status") == "planned"]),
            "executed_evidence": execute_evidence,
            "profile_command_count": profile_command_count,
        },
    }


def build_coding_design_trace(selected_tasks: list[dict[str, Any]]) -> dict[str, Any]:
    trace = []
    for task in selected_tasks:
        trace.append({"task_ref": task.get("task_id"), "design_artifact_refs": task.get("design_artifact_refs", []), "contract_refs": [], "acceptance_refs": task.get("done_when", []), "changed_files": task.get("changed_files", []), "endpoint": task.get("endpoint", "unknown"), "stack_profile": task.get("stack_profile", "default")})
    return {"trace": trace, "count": len(trace)}


def build_verification_handoff(selected_tasks: list[dict[str, Any]], changed_files: dict[str, Any], hook_results: list[dict[str, Any]], open_issues: list[dict[str, Any]], implementation_evidence: dict[str, Any]) -> dict[str, Any]:
    evidence_has_groups = any(
        bool(implementation_evidence.get(key, []))
        for key in ["compile_results", "lint_results", "integration_test_results", "contract_test_results", "smoke_results"]
    )
    failed_hooks = any(item.get("status") == "failed" for item in hook_results)
    return {
        "implemented_tasks": [str(t.get("task_id")) for t in selected_tasks],
        "changed_files": [item.get("path") for item in changed_files.get("files", [])],
        "expected_checks": sorted({str(item.get("hook")) for item in hook_results}),
        "acceptance_trace": [{"task_ref": str(t.get("task_id")), "acceptance_refs": t.get("done_when", []), "design_artifact_refs": t.get("design_artifact_refs", []), "endpoint": t.get("endpoint", "unknown"), "stack_profile": t.get("stack_profile", "default")} for t in selected_tasks],
        "known_risks": ["verification_hooks_not_executed"] if any(item.get("status") == "planned" for item in hook_results) else [],
        "open_issues": open_issues,
        "status": "blocked" if failed_hooks or not evidence_has_groups else "ready",
    }


def build_coding_summary(selected_batch: dict[str, Any], changed_files: dict[str, Any], coding_check_report: dict[str, Any], verification_handoff: dict[str, Any]) -> str:
    endpoint_counts: dict[str, int] = {}
    for task in selected_batch.get("selected_tasks", []):
        endpoint = str(task.get("endpoint", "unknown"))
        endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
    lines = ["# Coding Summary", "", f"- Status: {coding_check_report.get('summary', {}).get('status', 'unknown')}", f"- Selected tasks: {len(selected_batch.get('selected_tasks', []))}", f"- Changed files: {changed_files.get('count', 0)}", f"- Handoff status: {verification_handoff.get('status', 'unknown')}", "", "## Endpoint Breakdown"]
    if endpoint_counts:
        lines.extend([f"- {endpoint}: {count} task(s)" for endpoint, count in sorted(endpoint_counts.items())])
    else:
        lines.append("- None")
    lines.extend(["", "## Open Issues"])
    issues = coding_check_report.get("open_issues", [])
    lines.extend(["- None"] if not issues else [f"- {i.get('id')}: {i.get('summary')}" for i in issues])
    return "\n".join(lines) + "\n"


def build_coverage_issues(selected_batch: dict[str, Any], changed_files: dict[str, Any], hook_results: list[dict[str, Any]], implementation_evidence: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    selected_tasks = selected_batch.get("selected_tasks", [])
    hook_task_ids = {str(item.get("task_id")) for item in hook_results}
    missing_hooks = [task.get("task_id") for task in selected_tasks if str(task.get("task_id")) not in hook_task_ids]
    if missing_hooks:
        issues.append({"id": "coverage-hooks-missing", "summary": f"tasks missing verification hooks: {', '.join([str(i) for i in missing_hooks])}", "severity": "high"})
    all_changed = [str(item.get("path")) for item in changed_files.get("files", [])]
    if all_changed:
        evidence_count = sum(len(list(implementation_evidence.get(f"{group}_results", []))) for group in ["compile", "lint", "integration_test", "contract_test", "smoke"])
        if evidence_count == 0:
            issues.append({"id": "coverage-evidence-missing", "summary": "changed files exist but no evidence command results generated", "severity": "high"})
    missing_acceptance = [task.get("task_id") for task in selected_tasks if not task.get("done_when")]
    if missing_acceptance:
        issues.append({"id": "acceptance-trace-missing", "summary": f"tasks missing done_when acceptance refs: {', '.join([str(i) for i in missing_acceptance])}", "severity": "medium"})
    return issues


def build_drift_issues(selected_batch: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for task in selected_batch.get("selected_tasks", []):
        task_id = str(task.get("task_id"))
        if not task.get("design_artifact_refs"):
            issues.append({"id": f"drift-design-ref-{task_id}", "summary": f"task {task_id} missing design_artifact_refs", "severity": "high"})
        if not task.get("changed_files"):
            issues.append({"id": f"drift-changed-files-{task_id}", "summary": f"task {task_id} missing changed_files mapping", "severity": "high"})
    return issues


def resolve_schema_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    node: Any = schema
    for part in ref.lstrip("#/").split("/"):
        node = node.get(part, {})
    if not isinstance(node, dict):
        return {}
    return node


def validate_payload_against_schema(payload: Any, schema: dict[str, Any], root_schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    if "$ref" in schema:
        return validate_payload_against_schema(payload, resolve_schema_ref(root_schema, str(schema["$ref"])), root_schema, path)
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        valid = False
        for allowed in schema_type:
            if (allowed == "object" and isinstance(payload, dict)) or (allowed == "array" and isinstance(payload, list)) or (allowed == "string" and isinstance(payload, str)) or (allowed == "integer" and isinstance(payload, int) and not isinstance(payload, bool)) or (allowed == "boolean" and isinstance(payload, bool)) or (allowed == "null" and payload is None):
                valid = True
                break
        if not valid:
            errors.append(f"{path}: expected one of {schema_type}")
            return errors
    elif schema_type == "object":
        if not isinstance(payload, dict):
            return [f"{path}: expected object"]
        required = list(schema.get("required", []))
        for key in required:
            if key not in payload:
                errors.append(f"{path}: missing required field '{key}'")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in payload:
                if key not in properties:
                    errors.append(f"{path}: unknown field '{key}'")
        for key, subschema in properties.items():
            if key in payload and isinstance(subschema, dict):
                errors.extend(validate_payload_against_schema(payload[key], subschema, root_schema, f"{path}.{key}"))
        return errors
    elif schema_type == "array":
        if not isinstance(payload, list):
            return [f"{path}: expected array"]
        item_schema = schema.get("items", {})
        for idx, item in enumerate(payload):
            if isinstance(item_schema, dict):
                errors.extend(validate_payload_against_schema(item, item_schema, root_schema, f"{path}[{idx}]"))
        return errors
    elif schema_type == "string":
        if not isinstance(payload, str):
            return [f"{path}: expected string"]
    elif schema_type == "integer":
        if not (isinstance(payload, int) and not isinstance(payload, bool)):
            return [f"{path}: expected integer"]
    elif schema_type == "boolean":
        if not isinstance(payload, bool):
            return [f"{path}: expected boolean"]
    if "enum" in schema and payload not in list(schema.get("enum", [])):
        errors.append(f"{path}: value '{payload}' not in enum")
    return errors


def validate_artifacts(artifacts: dict[str, dict[str, Any]], schema_dir: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for name, payload in artifacts.items():
        schema_path = schema_dir / f"{name}.schema.json"
        if not schema_path.exists():
            issues.append({"id": f"schema-missing-{name}", "summary": f"schema missing for artifact {name}", "severity": "high"})
            continue
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = validate_payload_against_schema(payload, schema, schema)
        if errors:
            issues.append({"id": f"schema-validation-failed-{name}", "summary": f"{name} schema validation failed: {errors[0]}", "severity": "high"})
    return issues


def evaluate_gates(missing_inputs: list[str], design_gate_ok: bool, selected_batch: dict[str, Any], hook_results: list[dict[str, Any]], changed_files: dict[str, Any], implementation_evidence: dict[str, Any], verification_handoff: dict[str, Any], extra_issues: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues = []
    if missing_inputs:
        issues.append({"id": "coding-input-missing", "summary": f"missing required inputs: {', '.join(missing_inputs)}", "severity": "high"})
    if not design_gate_ok:
        issues.append({"id": "design-gate-not-ready", "summary": "design_check_report.summary.status is not passed/degraded", "severity": "high"})
    if selected_batch.get("unresolved_dependencies"):
        issues.append({"id": "task-dependencies-unresolved", "summary": "one or more selected candidates are blocked by dependencies", "severity": "medium"})
    if any(item.get("status") == "failed" for item in hook_results):
        issues.append({"id": "verification-hook-failed", "summary": "one or more verification hooks failed", "severity": "high"})
    if verification_handoff.get("status") != "ready":
        issues.append({"id": "handoff-not-ready", "summary": "verification handoff is blocked", "severity": "high"})
    issues.extend(build_coverage_issues(selected_batch, changed_files, hook_results, implementation_evidence))
    issues.extend(build_drift_issues(selected_batch))
    issues.extend(extra_issues)

    verification_failed = any(i["id"] == "verification-hook-failed" for i in issues)
    coverage_failed = any(i["id"] in {"coverage-hooks-missing", "coverage-evidence-missing"} for i in issues)
    input_failed = any(i["id"] in {"coding-input-missing", "design-gate-not-ready"} for i in issues)
    change_safety_failed = any(i["id"].startswith("drift-") for i in issues)
    handoff_failed = any(i["id"] in {"handoff-not-ready"} or i["id"].startswith("schema-validation-failed-") or i["id"].startswith("schema-missing-") for i in issues)
    gates = [
        {"gate_id": "coding_input_ready_gate", "status": "failed" if input_failed else "passed", "criteria_results": []},
        {"gate_id": "coding_change_safety_gate", "status": "failed" if change_safety_failed else "passed", "criteria_results": []},
        {"gate_id": "coding_verification_gate", "status": "failed" if verification_failed or coverage_failed else "passed", "criteria_results": []},
        {"gate_id": "coding_handoff_ready_gate", "status": "failed" if input_failed or verification_failed or handoff_failed else "passed", "criteria_results": []},
    ]
    return gates, issues


def build_verifier_results(selected_batch: dict[str, Any], gate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = any(g.get("status") == "failed" for g in gate_results)
    return [
        {"verifier_id": "coding_task_batch_readiness_verifier", "status": "passed" if not selected_batch.get("unresolved_dependencies") else "warning", "blocking": False, "findings": []},
        {"verifier_id": "coding_scope_conformance_verifier", "status": "failed" if failed else "passed", "blocking": failed, "findings": []},
    ]


def build_analyzer_results(gate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed_ids = [g.get("gate_id") for g in gate_results if g.get("status") == "failed"]
    if not failed_ids:
        return []
    return [{"analyzer_id": "coding_verification_analyzer", "failure_type": "gate_failed", "reasons": [", ".join(failed_ids)], "repair_actions": ["fix gates"], "resume_from": "coding.verify", "suggested_skill": "coding.verify", "suggested_command": "python scripts/run_coding_mission.py --inputs artifacts/coding/input_payload.json --output-dir artifacts/coding --execute-hooks --execute-evidence", "target_artifacts": ["artifacts/coding/coding_check_report.json"], "auto_fixable": False, "repair_plan": []}]


def build_coding_check_report(inputs: dict[str, Any], selected_batch: dict[str, Any], hook_results: list[dict[str, Any]], gate_results: list[dict[str, Any]], verifier_results: list[dict[str, Any]], analyzer_results: list[dict[str, Any]], open_issues: list[dict[str, Any]]) -> dict[str, Any]:
    blocking = len([i for i in open_issues if i.get("severity") == "high"])
    warnings = len([i for i in open_issues if i.get("severity") == "medium"])
    status = "failed" if blocking else ("degraded" if warnings else "passed")
    report = {"feature_id": inputs.get("feature_id", "unknown_feature"), "platform": selected_batch.get("platform", "cross"), "summary": {"status": status, "implemented_task_count": len(selected_batch.get("selected_tasks", [])), "blocking_issue_count": blocking, "warning_count": warnings}, "verifier_results": verifier_results, "gate_results": gate_results, "analyzer_results": analyzer_results, "open_issues": open_issues, "repair_actions": [] if status == "passed" else ["fix issues"]}
    if hook_results:
        report["verification_hook_results"] = hook_results
    return report


def run() -> int:
    args = build_parser().parse_args()
    inputs = load_json(args.inputs)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    missing = ensure_input_contract(inputs)
    design_ok = passed_design_gate(inputs.get("design_check_report", {}))
    selected, skipped, unresolved = select_ready_tasks(inputs.get("task_graph", {}), args.max_tasks)
    batch = build_selected_task_batch(inputs, selected, skipped, unresolved)
    hooks = run_task_hooks(batch.get("selected_tasks", []), args.execute_hooks)
    inputs["_selected_tasks"] = batch.get("selected_tasks", [])
    execution_context = build_execution_context(inputs, batch)
    task_report = build_task_execution_report(batch.get("selected_tasks", []), hooks)
    changed = build_changed_files(batch.get("selected_tasks", []))
    evidence = build_implementation_evidence(inputs, hooks, args.execute_evidence)
    design_trace = build_coding_design_trace(batch.get("selected_tasks", []))
    handoff = build_verification_handoff(batch.get("selected_tasks", []), changed, hooks, open_issues=[], implementation_evidence=evidence)
    schema_issues = validate_artifacts(
        {
            "execution_context": execution_context,
            "selected_task_batch": batch,
            "task_execution_report": task_report,
            "changed_files": changed,
            "implementation_evidence": evidence,
            "coding_design_trace": design_trace,
            "verification_handoff": handoff,
        },
        Path("docs/schemas/coding"),
    )
    gates, issues = evaluate_gates(missing, design_ok, batch, hooks, changed, evidence, handoff, schema_issues)
    handoff["open_issues"] = issues
    check_report = build_coding_check_report(inputs, batch, hooks, gates, build_verifier_results(batch, gates), build_analyzer_results(gates), issues)
    summary = build_coding_summary(batch, changed, check_report, handoff)

    write_json(output_dir / "execution_context.json", execution_context)
    write_json(output_dir / "selected_task_batch.json", batch)
    write_json(output_dir / "task_execution_report.json", task_report)
    write_json(output_dir / "changed_files.json", changed)
    write_json(output_dir / "implementation_evidence.json", evidence)
    write_json(output_dir / "coding_design_trace.json", design_trace)
    write_json(output_dir / "coding_check_report.json", check_report)
    write_json(output_dir / "verification_handoff.json", handoff)
    (output_dir / "coding_summary.md").write_text(summary, encoding="utf-8")

    print(json.dumps({"status": check_report["summary"]["status"], "output_dir": str(output_dir), "selected_task_count": len(batch["selected_tasks"]), "open_issue_count": len(check_report["open_issues"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
