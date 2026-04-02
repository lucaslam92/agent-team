"""
Data models for AADH.
All inter-module communication uses these typed dataclasses.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class FailureType(str, Enum):
    BUILD_ERROR      = "BUILD_ERROR"
    TEST_ERROR       = "TEST_ERROR"
    UI_NOT_FOUND     = "UI_NOT_FOUND"
    ACTION_FAILED    = "ACTION_FAILED"
    RUNTIME_CRASH    = "RUNTIME_CRASH"
    PARTIAL_SUCCESS  = "PARTIAL_SUCCESS"
    NONE             = "NONE"


class RunStatus(str, Enum):
    SUCCESS = "success"
    FAIL    = "fail"
    PARTIAL = "partial"


@dataclass
class Plan:
    task: str
    modules: list[str]              # Android modules affected, e.g. ["app"]
    files: list[str]                # Files to read/modify (relative to project root)
    acceptance_criteria: list[str]  # What "done" looks like
    verification_steps: list[str]   # Maestro YAML snippets or step descriptions
    risk_points: list[str]
    maestro_flow: str = ""          # Generated Maestro YAML (populated by planner)


@dataclass
class CodeChange:
    file_path: str          # Relative to project root
    original: str
    modified: str
    rationale: str


@dataclass
class CoderOutput:
    changes: list[CodeChange]
    change_summary: str
    iteration: int


@dataclass
class BuildResult:
    success: bool
    log: str
    apk_path: str = ""


@dataclass
class DeviceResult:
    success: bool
    log: str


@dataclass
class VerificationResult:
    success: bool
    log: str
    screenshots: list[Path] = field(default_factory=list)


@dataclass
class EvaluationResult:
    status: RunStatus
    failure_type: FailureType
    reason: str
    suggestion: str             # Diagnosis (NOT a rewrite) for the Coder
    next_action: str            # "fix_code" | "fix_test" | "stop"
    scores: dict[str, float] = field(default_factory=dict)


@dataclass
class RunArtifacts:
    run_id: str
    run_dir: Path
    task: str
    plan: Plan | None = None
    coder_output: CoderOutput | None = None
    build_result: BuildResult | None = None
    device_result: DeviceResult | None = None
    verification_result: VerificationResult | None = None
    evaluation: EvaluationResult | None = None
    iteration: int = 0


@dataclass
class FinalReport:
    task: str
    status: RunStatus
    total_iterations: int
    changed_files: list[str]
    evaluation: EvaluationResult
    run_dir: Path
