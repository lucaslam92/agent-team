"""
Gates — explicit pass/fail nodes. Roles never decide whether to continue.

Gate 1: Completeness     — after Completeness Checker
Gate 2: Platform Review  — after Platform Review Aggregator
Gate 3: Final PRD        — after Final PRD Compiler
"""

from __future__ import annotations
from dataclasses import dataclass
from prd_pipeline.models import (
    CompletenessReport, AggregatedPlatformReview, FinalPRD, GateStatus,
)


@dataclass
class GateResult:
    passed: bool
    reason: str


def gate1_completeness(report: CompletenessReport) -> GateResult:
    if report.status == GateStatus.BLOCKED:
        items = "\n".join(f"  - {m}" for m in report.missing_info)
        return GateResult(
            passed=False,
            reason=f"Missing required information:\n{items}",
        )
    return GateResult(passed=True, reason="Completeness check passed.")


def gate2_platform_review(aggregated: AggregatedPlatformReview) -> GateResult:
    if aggregated.has_blocking_issue:
        items = "\n".join(f"  - {r}" for r in aggregated.blocking_reasons)
        return GateResult(
            passed=False,
            reason=f"Blocking platform issues:\n{items}",
        )
    return GateResult(passed=True, reason="All platforms feasible.")


def gate3_final_prd(prd: FinalPRD) -> GateResult:
    errors: list[str] = []

    if not prd.features:
        errors.append("No features defined.")

    for f in prd.features:
        if not f.flow.user_flow:
            errors.append(f"Feature '{f.name}': missing user_flow.")
        if not f.flow.expected_behavior:
            errors.append(f"Feature '{f.name}': missing expected_behavior.")
        if not f.implementation.approach:
            errors.append(f"Feature '{f.name}': missing implementation approach.")
        if not f.implementation.platform_alignment:
            errors.append(f"Feature '{f.name}': missing platform_alignment.")

    if not prd.acceptance_criteria:
        errors.append("No acceptance_criteria defined.")

    if errors:
        return GateResult(passed=False, reason="\n".join(f"  - {e}" for e in errors))

    return GateResult(passed=True, reason="Final PRD is complete and valid.")
