#!/usr/bin/env python3
"""Run Coding Mission gates and verifiers, then write coding_check_report.json.

Reads all coding artifacts produced so far (selected_task_batch, hook_results,
changed_files, implementation_evidence) and evaluates the four gates:
  1. coding_input_ready_gate
  2. coding_change_safety_gate
  3. coding_verification_gate
  4. coding_handoff_ready_gate

Writes:
  - coding_check_report.json
  - verification_handoff.json (updated with open_issues)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_coding_mission import (
    build_analyzer_results,
    build_coding_check_report,
    build_coding_design_trace,
    build_implementation_evidence,
    build_verifier_results,
    build_verification_handoff,
    ensure_input_contract,
    evaluate_gates,
    load_json,
    passed_design_gate,
    validate_artifacts,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Coding Mission gates and write coding_check_report.json."
    )
    parser.add_argument("--inputs", required=True, help="Path to input_payload.json")
    parser.add_argument(
        "--selected-task-batch",
        required=True,
        help="Path to selected_task_batch.json",
    )
    parser.add_argument(
        "--hook-results",
        default=None,
        help="Path to hook_results.json (written by coding-run-verification-hooks)",
    )
    parser.add_argument(
        "--changed-files",
        default=None,
        help="Path to changed_files.json (written after execute_tasks)",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/coding",
        help="Directory to write coding_check_report.json and verification_handoff.json",
    )
    parser.add_argument(
        "--execute-evidence",
        action="store_true",
        help="Actually run evidence commands (compile/lint/etc.) instead of planning",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    inputs = load_json(args.inputs)
    batch = load_json(args.selected_task_batch)
    selected_tasks = batch.get("selected_tasks", [])

    # Load optional artifacts (may not exist yet at verify time)
    hook_results: list = []
    if args.hook_results and Path(args.hook_results).exists():
        hook_results = load_json(args.hook_results).get("hook_results", [])

    changed_files: dict = {"files": [], "count": 0}
    if args.changed_files and Path(args.changed_files).exists():
        changed_files = load_json(args.changed_files)

    missing = ensure_input_contract(inputs)
    design_ok = passed_design_gate(inputs.get("design_check_report", {}))
    evidence = build_implementation_evidence(inputs, selected_tasks, hook_results, args.execute_evidence)
    design_trace = build_coding_design_trace(selected_tasks)
    handoff = build_verification_handoff(selected_tasks, changed_files, hook_results, open_issues=[], implementation_evidence=evidence)

    schema_dir = Path(__file__).resolve().parent.parent / "docs/schemas/coding"
    schema_issues = validate_artifacts(
        {
            "selected_task_batch": batch,
            "changed_files": changed_files,
            "implementation_evidence": evidence,
            "coding_design_trace": design_trace,
            "verification_handoff": handoff,
        },
        schema_dir,
    )

    gates, issues = evaluate_gates(missing, design_ok, batch, hook_results, changed_files, evidence, handoff, schema_issues)
    handoff["open_issues"] = issues
    check_report = build_coding_check_report(
        inputs, batch, hook_results, gates,
        build_verifier_results(batch, gates),
        build_analyzer_results(gates),
        issues,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "coding_check_report.json", check_report)
    write_json(output_dir / "coding_design_trace.json", design_trace)
    write_json(output_dir / "verification_handoff.json", handoff)

    status = check_report["summary"]["status"]
    print(
        json.dumps(
            {
                "status": status,
                "output_dir": str(output_dir),
                "blocking_issue_count": check_report["summary"]["blocking_issue_count"],
                "warning_count": check_report["summary"]["warning_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
