"""
Artifact management — every run gets a timestamped directory.

artifacts/run_<timestamp>/
├── task.txt
├── plan.json
├── diff.patch
├── build.log
├── maestro.log
├── logcat.txt
├── screenshots/
└── report.md
"""

from __future__ import annotations
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

from aadh.core.models import (
    Plan, CoderOutput, BuildResult, DeviceResult,
    VerificationResult, EvaluationResult, FinalReport, RunStatus,
)


class ArtifactStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def new_run(self, task: str) -> tuple[str, Path]:
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "screenshots").mkdir()
        (run_dir / "task.txt").write_text(task, encoding="utf-8")
        return run_id, run_dir

    def save_plan(self, run_dir: Path, plan: Plan) -> None:
        data = {
            "task": plan.task,
            "modules": plan.modules,
            "files": plan.files,
            "acceptance_criteria": plan.acceptance_criteria,
            "verification_steps": plan.verification_steps,
            "risk_points": plan.risk_points,
            "maestro_flow": plan.maestro_flow,
        }
        (run_dir / "plan.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def save_coder_output(self, run_dir: Path, coder_output: CoderOutput) -> None:
        # Write unified diff
        diff_lines = []
        for change in coder_output.changes:
            diff_lines.append(f"--- a/{change.file_path}")
            diff_lines.append(f"+++ b/{change.file_path}")
            # Generate a minimal diff representation
            orig_lines = change.original.splitlines(keepends=True)
            mod_lines  = change.modified.splitlines(keepends=True)
            import difflib
            diff_lines.extend(
                difflib.unified_diff(orig_lines, mod_lines, lineterm="")
            )
            diff_lines.append("")
        (run_dir / "diff.patch").write_text(
            "\n".join(diff_lines), encoding="utf-8"
        )
        (run_dir / "change_summary.txt").write_text(
            coder_output.change_summary, encoding="utf-8"
        )

    def save_build_log(self, run_dir: Path, result: BuildResult) -> None:
        (run_dir / "build.log").write_text(result.log, encoding="utf-8")

    def save_maestro_log(self, run_dir: Path, result: VerificationResult) -> None:
        (run_dir / "maestro.log").write_text(result.log, encoding="utf-8")

    def save_logcat(self, run_dir: Path, logcat: str) -> None:
        (run_dir / "logcat.txt").write_text(logcat, encoding="utf-8")

    def save_evaluation(self, run_dir: Path, evaluation: EvaluationResult) -> None:
        data = {
            "status": evaluation.status.value,
            "failure_type": evaluation.failure_type.value,
            "reason": evaluation.reason,
            "suggestion": evaluation.suggestion,
            "next_action": evaluation.next_action,
            "scores": evaluation.scores,
        }
        (run_dir / "evaluation.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def write_report(self, run_dir: Path, report: FinalReport) -> Path:
        status_icon = "✅" if report.status == RunStatus.SUCCESS else \
                      "⚠️" if report.status == RunStatus.PARTIAL else "❌"
        lines = [
            "# Run Report",
            "",
            f"## Task",
            report.task,
            "",
            f"## Result",
            f"{status_icon} {report.status.value.upper()}",
            "",
            "## Changes",
            *[f"- {f}" for f in report.changed_files],
            "",
            "## Verification",
            f"- Status: {report.evaluation.failure_type.value}",
            f"- Reason: {report.evaluation.reason}",
            "",
            f"## Iterations",
            f"Completed in {report.total_iterations} iteration(s)",
            "",
            "## Notes",
            report.evaluation.suggestion or "—",
        ]
        path = run_dir / "report.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
