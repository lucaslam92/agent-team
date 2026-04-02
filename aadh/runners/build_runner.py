"""
Build Runner — Executes Gradle build and captures output.
"""

from __future__ import annotations
import subprocess
from pathlib import Path

from aadh.core.models import BuildResult


def build(
    project_path: Path,
    assemble_cmd: str,
    apk_relative_path: str,
) -> BuildResult:
    result = _run(assemble_cmd, cwd=project_path)

    apk_path = ""
    if result.returncode == 0:
        candidate = project_path / apk_relative_path
        apk_path = str(candidate) if candidate.exists() else ""

    return BuildResult(
        success=(result.returncode == 0),
        log=result.stdout + result.stderr,
        apk_path=apk_path,
    )


def run_unit_tests(
    project_path: Path,
    unit_test_cmd: str,
) -> BuildResult:
    result = _run(unit_test_cmd, cwd=project_path)
    return BuildResult(
        success=(result.returncode == 0),
        log=result.stdout + result.stderr,
    )


def _run(cmd: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        shell=True,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
