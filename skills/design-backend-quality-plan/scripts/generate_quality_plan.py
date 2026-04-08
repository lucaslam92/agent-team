#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-backend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from backend_design_lib import (  # noqa: E402
    acceptance_items,
    feature_identity,
    load_json,
    requirement_lines,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate backend quality_plan.json and risk_register.json.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--knowbase-context", required=True)
    parser.add_argument("--quality-output", required=True)
    parser.add_argument("--risk-output", required=True)
    return parser


def strategy(summary: str, acceptance_refs: list[str], actions: list[str]) -> dict[str, object]:
    return {
        "summary": summary,
        "actions": actions,
        "acceptance_refs": acceptance_refs,
    }


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    knowbase_context = load_json(args.knowbase_context)
    feature_id, feature_name = feature_identity(final_prd)
    acceptance_refs = [item["ref"] for item in acceptance_items(final_prd)]
    requirements = requirement_lines(final_prd)

    quality_plan = {
        "feature_id": feature_id,
        "idempotency_strategy": strategy(
            f"Use request identity to make {feature_name} writes retry-safe.",
            acceptance_refs,
            ["Require request_id or business key on write paths.", "Persist terminal state before emitting success."],
        ),
        "consistency_strategy": strategy(
            "Keep write-side consistency inside the owning backend boundary.",
            acceptance_refs,
            ["Apply state transition and side effects in a single service-owned boundary.", "Record async publication intent before acknowledge."],
        ),
        "concurrency_control": strategy(
            "Prevent concurrent conflicting writes.",
            acceptance_refs,
            ["Use optimistic version checks or compare-and-set on mutable state."],
        ),
        "permission_model": strategy(
            "Enforce backend authorization before state changes.",
            acceptance_refs,
            ["Validate caller identity and role at contract entry point."],
        ),
        "observability": strategy(
            "Emit logs, metrics, and alerts for critical state transitions.",
            acceptance_refs,
            ["Track request latency, error rate, and async failure count."],
        ),
        "rollout_plan": strategy(
            "Ship behind a controlled rollout boundary.",
            acceptance_refs,
            ["Use a feature flag or traffic gate for the first release."],
        ),
        "rollback_plan": strategy(
            "Keep rollback steps deterministic and documented.",
            acceptance_refs,
            ["Disable the new entry point and revert migration-dependent writes if required."],
        ),
    }
    risks = [
        {
            "id": "risk_missing_context",
            "summary": gap["summary"],
            "severity": gap["severity"],
            "impact": "Design may miss stack or architecture constraints.",
            "mitigation": gap["recommended_action"],
            "blocking": gap["severity"] == "high",
        }
        for gap in knowbase_context.get("unresolved_gaps", [])
    ]
    if any("latency" in line.lower() or "performance" in line.lower() for line in requirements):
        risks.append(
            {
                "id": "risk_performance_budget",
                "summary": "Performance-sensitive requirement needs explicit capacity validation.",
                "severity": "medium",
                "impact": "Feature may violate latency or throughput targets under load.",
                "mitigation": "Add load-test and capacity review before coding exit.",
                "blocking": False,
            }
        )
    write_json(args.quality_output, quality_plan)
    write_json(args.risk_output, {"feature_id": feature_id, "risks": risks})


if __name__ == "__main__":
    main()
