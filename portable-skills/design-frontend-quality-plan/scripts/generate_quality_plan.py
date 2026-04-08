#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-frontend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from frontend_design_lib import acceptance_items, feature_identity, load_json, requirement_lines, write_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate frontend quality_plan.json and risk_register.json.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--knowbase-context", required=True)
    parser.add_argument("--quality-output", required=True)
    parser.add_argument("--risk-output", required=True)
    return parser


def strategy(summary: str, acceptance_refs: list[str], actions: list[str]) -> dict[str, object]:
    return {"summary": summary, "actions": actions, "acceptance_refs": acceptance_refs}


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    knowbase_context = load_json(args.knowbase_context)
    feature_id, feature_name = feature_identity(final_prd)
    acceptance_refs = [item["ref"] for item in acceptance_items(final_prd)]
    requirements = requirement_lines(final_prd)
    quality_plan = {
        "feature_id": feature_id,
        "accessibility": strategy("Preserve keyboard, screen-reader, and semantics coverage for the feature.", acceptance_refs, ["Keep focus flow deterministic.", "Expose meaningful labels and status updates."]),
        "performance_budget": strategy("Prevent page-level performance regressions.", acceptance_refs, ["Avoid blocking initial render on optional data.", "Keep component recomputation bounded."]),
        "state_consistency": strategy("Keep UI state aligned with backend contract and local optimistic rules.", acceptance_refs, ["Single-source server state transitions.", "Reset transient state after terminal outcomes."]),
        "error_handling": strategy("Show actionable error messages and retry paths.", acceptance_refs, ["Map retryable errors to retry UI.", "Keep blocking validation inline."]),
        "observability": strategy("Expose user interaction and failure telemetry.", acceptance_refs, ["Track key CTA, load, success, and failure events."]),
        "rollout_plan": strategy("Release safely behind a feature switch when needed.", acceptance_refs, ["Support runtime enable/disable boundary."]),
        "fallback_plan": strategy("Provide degraded UI when contract or data is temporarily unavailable.", acceptance_refs, ["Fallback empty/error states stay usable."]),
    }
    risks = [
        {
            "id": gap["id"],
            "summary": gap["summary"],
            "severity": gap["severity"],
            "impact": "Frontend design may miss platform-specific constraints.",
            "mitigation": gap["recommended_action"],
            "blocking": gap["severity"] == "high",
        }
        for gap in knowbase_context.get("unresolved_gaps", [])
    ]
    if any("performance" in line.lower() or "latency" in line.lower() for line in requirements):
        risks.append(
            {
                "id": "risk_performance_budget",
                "summary": "Feature includes performance-sensitive UX expectations.",
                "severity": "medium",
                "impact": "Rendering or data binding may exceed acceptable budget.",
                "mitigation": "Add performance review and targeted smoke checks before coding exit.",
                "blocking": False,
            }
        )
    write_json(args.quality_output, quality_plan)
    write_json(args.risk_output, {"feature_id": feature_id, "risks": risks})


if __name__ == "__main__":
    main()
