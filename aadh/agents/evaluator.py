"""
Evaluator Agent — Analyzes all run artifacts and classifies the outcome.

Key principle: the Evaluator is a judge, not a fixer.
It diagnoses WHAT failed (with evidence from logs).
It never suggests HOW to rewrite code — that collapses generation quality.

Failure types (must cover all cases):
  BUILD_ERROR      — Gradle compilation failure
  TEST_ERROR       — Unit test failure
  UI_NOT_FOUND     — Maestro can't locate a UI element
  ACTION_FAILED    — Maestro action (tap, scroll) had no effect
  RUNTIME_CRASH    — crash or ANR detected in logcat
  PARTIAL_SUCCESS  — Some criteria met but not all
  NONE             — All criteria met
"""

from __future__ import annotations
import json
import re

from aadh.core.llm import LLMClient
from aadh.core.models import (
    Plan, BuildResult, VerificationResult, EvaluationResult,
    FailureType, RunStatus,
)


SYSTEM = """\
You are an evaluator agent for an Android development harness.
You read build logs, Maestro test output, and logcat to judge whether a run succeeded.

Rules:
1. Classify the failure type using EXACTLY one of:
   BUILD_ERROR | TEST_ERROR | UI_NOT_FOUND | ACTION_FAILED | RUNTIME_CRASH | PARTIAL_SUCCESS | NONE
2. NONE means complete success — all acceptance criteria met.
3. Base your diagnosis strictly on the evidence in the logs. Do not speculate.
4. feedback_for_coder: 3-6 bullet points describing WHAT is wrong (no code, no fixes).
5. feedback_for_planner: 1-2 sentences — is the plan itself wrong, or is this a code execution problem?
6. next_action: one of "fix_code" | "fix_plan" | "stop"
   - fix_code:  the plan is sound but the code has bugs
   - fix_plan:  the plan specified wrong files or wrong criteria
   - stop:      success, or failure is unrecoverable within allowed iterations

Score each dimension 0–10:
  build_success (0=failed to compile, 10=clean build)
  ui_correctness (0=crash/nothing visible, 10=all UI elements found and correct)
  criteria_coverage (0=no criteria met, 10=all criteria verified)

Respond with ONLY valid JSON (no markdown fences):
{
  "status": "success | fail | partial",
  "failure_type": "NONE | BUILD_ERROR | ...",
  "reason": "one sentence — what specifically went wrong",
  "feedback_for_coder": "bullet-point diagnostic (use \\n- for each point)",
  "feedback_for_planner": "1-2 sentences",
  "next_action": "fix_code | fix_plan | stop",
  "scores": {
    "build_success": 0,
    "ui_correctness": 0,
    "criteria_coverage": 0
  }
}"""


def evaluate(
    client: LLMClient,
    plan: Plan,
    build_result: BuildResult,
    verification_result: VerificationResult | None,
    logcat: str,
    iteration: int,
) -> EvaluationResult:
    # ── Fast-path: build failed ───────────────────────────────────────────────
    if not build_result.success:
        error_excerpt = _extract_build_errors(build_result.log)
        return EvaluationResult(
            status=RunStatus.FAIL,
            failure_type=FailureType.BUILD_ERROR,
            reason=f"Gradle build failed. First error: {error_excerpt[:200]}",
            suggestion=f"Build errors:\n{error_excerpt}",
            next_action="fix_code",
            scores={"build_success": 0, "ui_correctness": 0, "criteria_coverage": 0},
        )

    # ── LLM-based evaluation for runtime/UI failures ─────────────────────────
    parts = [
        f"Task: {plan.task}",
        "",
        "Acceptance criteria:",
        *[f"  - {c}" for c in plan.acceptance_criteria],
        "",
        f"Iteration: {iteration}",
        "",
        "=== BUILD LOG (last 100 lines) ===",
        _tail(build_result.log, 100),
        "",
        "=== MAESTRO TEST LOG ===",
        (verification_result.log if verification_result else "(Maestro did not run)"),
        "",
        "=== LOGCAT (crash-relevant lines) ===",
        _filter_logcat(logcat),
    ]

    raw = client.chat(system=SYSTEM, user="\n".join(parts))

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    data = json.loads(raw)

    status_map = {"success": RunStatus.SUCCESS, "fail": RunStatus.FAIL, "partial": RunStatus.PARTIAL}
    ft_map = {ft.value: ft for ft in FailureType}

    status       = status_map.get(data.get("status", "fail"), RunStatus.FAIL)
    failure_type = ft_map.get(data.get("failure_type", "NONE"), FailureType.NONE)

    return EvaluationResult(
        status=status,
        failure_type=failure_type,
        reason=data.get("reason", ""),
        suggestion=data.get("feedback_for_coder", ""),
        next_action=data.get("next_action", "fix_code"),
        scores=data.get("scores", {}),
    )


def _tail(text: str, n: int) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-n:]) if len(lines) > n else text


def _filter_logcat(logcat: str) -> str:
    """Keep only crash-relevant lines to save tokens."""
    keywords = ("FATAL", "AndroidRuntime", "Exception", "Error", "ANR", "Caused by")
    lines = [l for l in logcat.splitlines() if any(k in l for k in keywords)]
    return "\n".join(lines[:80]) or "(no crashes detected)"


def _extract_build_errors(log: str) -> str:
    """Pull the first FAILURE block from Gradle output."""
    lines = log.splitlines()
    errors: list[str] = []
    in_error = False
    for line in lines:
        if "error:" in line.lower() or "FAILURE" in line or "Exception" in line:
            in_error = True
        if in_error:
            errors.append(line)
            if len(errors) > 30:
                break
    return "\n".join(errors) if errors else log[-2000:]
