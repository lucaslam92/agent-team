#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read analyzer repair plans from design_check_report.json and optionally execute them.")
    parser.add_argument("--report", required=True, help="Path to backend/frontend design_check_report.json")
    parser.add_argument("--analyzer-id", help="Only run steps from the selected analyzer.")
    parser.add_argument("--step-id", help="Only run the selected repair step.")
    parser.add_argument("--execute", action="store_true", help="Execute commands instead of printing the plan.")
    parser.add_argument("--include-non-auto-fixable", action="store_true", help="Include steps marked auto_fixable=false.")
    parser.add_argument("--max-steps", type=int, help="Optional maximum number of steps to include.")
    parser.add_argument("--workdir", help="Working directory for command execution. Defaults to the current process cwd.")
    return parser


def load_report(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def selected_steps(
    report: dict[str, object],
    analyzer_id: str | None,
    step_id: str | None,
    include_non_auto_fixable: bool,
    max_steps: int | None,
) -> list[dict[str, object]]:
    analyzers = report.get("analyzer_results", [])
    selected: list[dict[str, object]] = []
    for analyzer in analyzers:
        if analyzer_id and analyzer.get("analyzer_id") != analyzer_id:
            continue
        for step in analyzer.get("repair_plan", []):
            if step_id and step.get("step_id") != step_id:
                continue
            if not include_non_auto_fixable and not step.get("auto_fixable", False):
                continue
            selected.append(
                {
                    "analyzer_id": analyzer.get("analyzer_id"),
                    "failure_type": analyzer.get("failure_type"),
                    "step_id": step.get("step_id"),
                    "summary": step.get("summary"),
                    "skill": step.get("skill"),
                    "target_artifacts": step.get("target_artifacts", []),
                    "auto_fixable": step.get("auto_fixable", False),
                    "command": step.get("command", ""),
                }
            )
    if max_steps is not None:
        return selected[:max_steps]
    return selected


def print_plan(steps: list[dict[str, object]]) -> None:
    payload = {
        "mode": "dry_run",
        "step_count": len(steps),
        "steps": steps,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def execute_plan(steps: list[dict[str, object]], workdir: str) -> int:
    for index, step in enumerate(steps, start=1):
        command = str(step.get("command") or "").strip()
        if not command:
            print(f"[{index}/{len(steps)}] skip {step.get('step_id')}: missing command", file=sys.stderr)
            return 1
        print(f"[{index}/{len(steps)}] {step.get('step_id')} -> {command}")
        completed = subprocess.run(command, shell=True, cwd=workdir)
        if completed.returncode != 0:
            print(f"step failed: {step.get('step_id')} (exit {completed.returncode})", file=sys.stderr)
            return completed.returncode
    print(json.dumps({"mode": "execute", "step_count": len(steps), "status": "completed"}, ensure_ascii=False))
    return 0


def main() -> None:
    args = build_parser().parse_args()
    report = load_report(args.report)
    steps = selected_steps(
        report=report,
        analyzer_id=args.analyzer_id,
        step_id=args.step_id,
        include_non_auto_fixable=args.include_non_auto_fixable,
        max_steps=args.max_steps,
    )
    if not steps:
        print(json.dumps({"mode": "empty", "step_count": 0, "status": "no_matching_steps"}, ensure_ascii=False))
        return
    if not args.execute:
        print_plan(steps)
        return
    sys.exit(execute_plan(steps, args.workdir or str(Path.cwd())))


if __name__ == "__main__":
    main()
