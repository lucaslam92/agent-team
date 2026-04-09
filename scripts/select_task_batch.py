#!/usr/bin/env python3
"""Select ready task batch from task_graph.

Validates the input contract and design gate, then selects the ready task batch.
Outputs selected_task_batch.json only — does not run hooks or build evidence.
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
    build_selected_task_batch,
    ensure_input_contract,
    load_json,
    passed_design_gate,
    select_ready_tasks,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate inputs and select ready task batch from task_graph."
    )
    parser.add_argument("--inputs", required=True, help="Path to input_payload.json")
    parser.add_argument(
        "--output",
        default="artifacts/coding/selected_task_batch.json",
        help="Path to write selected_task_batch.json",
    )
    parser.add_argument(
        "--max-tasks", type=int, default=10, help="Maximum tasks to include in batch"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    inputs = load_json(args.inputs)

    missing = ensure_input_contract(inputs)
    if missing:
        print(
            json.dumps(
                {"status": "failed", "error": f"missing required inputs: {', '.join(missing)}"},
                ensure_ascii=False,
            )
        )
        return 1

    if not passed_design_gate(inputs.get("design_check_report", {})):
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": "design_check_report.summary.status is not passed/degraded",
                },
                ensure_ascii=False,
            )
        )
        return 1

    selected, skipped, unresolved = select_ready_tasks(
        inputs.get("task_graph", {}), args.max_tasks
    )
    batch = build_selected_task_batch(inputs, selected, skipped, unresolved)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, batch)

    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output),
                "selected_task_count": len(batch["selected_tasks"]),
                "skipped_task_count": len(batch["skipped_tasks"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
