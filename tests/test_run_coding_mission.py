from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_coding_mission as rcm


def base_inputs() -> dict:
    return {
        "feature_id": "feature-x",
        "final_prd": {},
        "repo_context": {"services": ["api"]},
        "knowbase_context": {},
        "design_assets": {"domain_model": {}, "api_contract": {}},
        "task_graph": {
            "platform": "backend",
            "checkpoint": "cp1",
            "sources": ["artifacts/design/backend/backend_task_graph.json"],
            "tasks": [
                {
                    "task_id": "T1",
                    "task_type": "domain",
                    "priority": "high",
                    "checkpoint": "cp1",
                    "depends_on": [],
                    "design_artifact_refs": ["domain_model.json"],
                    "done_when": ["domain model compiles"],
                    "verification_hooks": ["python -c \"print('ok')\""],
                    "changed_files": ["src/domain/user.py"],
                    "endpoint": "backend",
                    "stack_profile": "python-fastapi",
                },
                {
                    "task_id": "T2",
                    "task_type": "api",
                    "priority": "medium",
                    "checkpoint": "cp1",
                    "depends_on": ["DONE"],
                    "design_artifact_refs": ["api_contract.yaml"],
                    "done_when": ["api contract checks pass"],
                    "status": "todo",
                    "changed_files": ["src/api/user_routes.py"],
                    "endpoint": "web-frontend",
                    "stack_profile": "react-vite",
                },
                {"task_id": "DONE", "status": "done"},
            ],
        },
        "design_check_report": {"summary": {"status": "passed"}},
        "verification_plan": {
            "endpoint_profiles": {
                "backend::python-fastapi": {
                    "compile": ["echo compile-backend"],
                    "lint": ["echo lint-backend"],
                },
                "web-frontend::react-vite": {
                    "compile": ["echo compile-web"],
                    "lint": ["echo lint-web"],
                },
            }
        },
    }


def test_select_ready_tasks_and_unresolved_dependencies() -> None:
    inputs = base_inputs()
    selected, skipped, unresolved = rcm.select_ready_tasks(inputs["task_graph"], max_tasks=10)
    assert [task["task_id"] for task in selected] == ["T1", "T2"]
    assert unresolved == []
    assert skipped == []


def test_gate_failure_when_input_missing() -> None:
    inputs = base_inputs()
    inputs.pop("final_prd")
    missing = rcm.ensure_input_contract(inputs)
    selected, skipped, unresolved = rcm.select_ready_tasks(inputs["task_graph"], max_tasks=10)
    batch = rcm.build_selected_task_batch(inputs, selected, skipped, unresolved)
    hooks = rcm.run_task_hooks(batch["selected_tasks"], execute_hooks=False)
    changed = rcm.build_changed_files(batch["selected_tasks"])
    evidence = rcm.build_implementation_evidence({"_selected_tasks": batch["selected_tasks"]}, hooks, execute_evidence=False)
    handoff = rcm.build_verification_handoff(batch["selected_tasks"], changed, hooks, open_issues=[], implementation_evidence=evidence)
    gates, issues = rcm.evaluate_gates(missing, True, batch, hooks, changed, evidence, handoff, [])
    assert any(gate["gate_id"] == "coding_input_ready_gate" and gate["status"] == "failed" for gate in gates)
    assert any(issue["id"] == "coding-input-missing" for issue in issues)


def test_verification_gate_fails_on_failed_hook() -> None:
    batch = {
        "selected_tasks": [
            {
                "task_id": "T1",
                "verification_hooks": ["python -c \"import sys; sys.exit(2)\""],
                "design_artifact_refs": ["domain_model.json"],
            }
        ],
        "unresolved_dependencies": [],
    }
    hooks = rcm.run_task_hooks(batch["selected_tasks"], execute_hooks=True)
    changed = {"files": [], "count": 0}
    evidence = rcm.build_implementation_evidence({"_selected_tasks": batch["selected_tasks"]}, hooks, execute_evidence=False)
    handoff = rcm.build_verification_handoff(batch["selected_tasks"], changed, hooks, open_issues=[], implementation_evidence=evidence)
    gates, issues = rcm.evaluate_gates([], True, batch, hooks, changed, evidence, handoff, [])
    assert any(gate["gate_id"] == "coding_verification_gate" and gate["status"] == "failed" for gate in gates)
    assert any(issue["id"] == "verification-hook-failed" for issue in issues)


def test_build_changed_files_handoff_and_new_core_artifacts() -> None:
    inputs = base_inputs()
    selected, skipped, unresolved = rcm.select_ready_tasks(inputs["task_graph"], max_tasks=2)
    batch = rcm.build_selected_task_batch(inputs, selected, skipped, unresolved)
    hooks = rcm.run_task_hooks(batch["selected_tasks"], execute_hooks=False)

    changed = rcm.build_changed_files(batch["selected_tasks"])
    execution_context = rcm.build_execution_context(inputs, batch)
    inputs["_selected_tasks"] = batch["selected_tasks"]
    implementation_evidence = rcm.build_implementation_evidence(inputs, hooks, execute_evidence=False)
    handoff = rcm.build_verification_handoff(batch["selected_tasks"], changed, hooks, open_issues=[], implementation_evidence=implementation_evidence)
    design_trace = rcm.build_coding_design_trace(batch["selected_tasks"])

    assert changed["count"] == 2
    assert handoff["status"] == "ready"
    assert execution_context["selected_checkpoint"] == "cp1"
    assert any("backend::python-fastapi" == item for item in execution_context["endpoint_profiles"])
    assert implementation_evidence["summary"]["planned_hook_count"] >= 1
    assert design_trace["count"] == len(batch["selected_tasks"])
    assert changed["files"][0]["endpoint"] in {"backend", "web-frontend"}




def test_build_implementation_evidence_with_plan_commands() -> None:
    inputs = base_inputs()
    inputs["verification_plan"] = {"endpoint_profiles": {"backend::python-fastapi": {"compile": ["echo compile"], "lint": ["echo lint"], "integration": ["echo int"], "contract": ["echo contract"], "smoke": ["echo smoke"]}}}
    inputs["_selected_tasks"] = [
        {
            "task_id": "T1",
            "endpoint": "backend",
            "stack_profile": "python-fastapi",
        }
    ]
    hooks = [{"task_id": "T1", "hook": "pytest -q", "status": "planned", "exit_code": None}]
    evidence = rcm.build_implementation_evidence(inputs, hooks, execute_evidence=False)
    assert evidence["summary"]["executed_evidence"] is False
    assert evidence["compile_results"][0]["status"] == "planned"
    assert evidence["lint_results"][0]["status"] == "planned"
    assert evidence["summary"]["profile_command_count"]["backend::python-fastapi"] == 5


def test_validate_artifacts_reports_schema_issues() -> None:
    issues = rcm.validate_artifacts({"selected_task_batch": {"invalid": True}}, ROOT / "docs/schemas/coding")
    assert any(issue["id"] == "schema-validation-failed-selected_task_batch" for issue in issues)


def test_split_execute_scripts_and_compile_report(tmp_path: Path) -> None:
    batch = {
        "selected_tasks": [
            {"task_id": "T1", "endpoint": "backend", "verification_hooks": ["python -c \"print('ok')\""]},
            {"task_id": "T2", "endpoint": "web-frontend", "verification_hooks": ["python -c \"print('ok')\""]},
        ]
    }
    batch_path = tmp_path / "selected_task_batch.json"
    batch_path.write_text(json.dumps(batch), encoding="utf-8")

    backend_out = tmp_path / "backend_task_execution.json"
    frontend_out = tmp_path / "frontend_task_execution.json"
    subprocess.run([sys.executable, "scripts/coding_backend_execute_tasks.py", "--selected-task-batch", str(batch_path), "--output", str(backend_out)], check=True)
    subprocess.run([sys.executable, "scripts/coding_frontend_execute_tasks.py", "--selected-task-batch", str(batch_path), "--output", str(frontend_out)], check=True)

    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "selected_task_batch.json").write_text(json.dumps({"selected_tasks": batch["selected_tasks"]}), encoding="utf-8")
    (artifacts / "changed_files.json").write_text(json.dumps({"files": [], "count": 0}), encoding="utf-8")
    (artifacts / "coding_check_report.json").write_text(json.dumps({"summary": {"status": "passed"}, "open_issues": []}), encoding="utf-8")
    (artifacts / "verification_handoff.json").write_text(json.dumps({"status": "ready"}), encoding="utf-8")
    subprocess.run([sys.executable, "scripts/coding_compile_report.py", "--artifacts-dir", str(artifacts)], check=True)
    assert (artifacts / "coding_summary.md").exists()

def test_run_verification_hooks_script(tmp_path: Path) -> None:
    batch = {
        "selected_tasks": [
            {"task_id": "T1", "verification_hooks": ["python -c \"print('ok')\""]}
        ]
    }
    batch_path = tmp_path / "selected_task_batch.json"
    out_path = tmp_path / "hook_results.json"
    batch_path.write_text(json.dumps(batch), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_verification_hooks.py",
            "--selected-task-batch",
            str(batch_path),
            "--output",
            str(out_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["count"] == 1
    assert payload["hook_results"][0]["status"] == "planned"
