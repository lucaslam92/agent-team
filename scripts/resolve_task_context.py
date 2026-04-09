#!/usr/bin/env python3
"""Build execution_context.json for the selected coding task batch.

Reads the input payload and the already-selected task batch, then resolves
and persists a structured execution context for downstream skills to consume.
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
    build_execution_context,
    load_json,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build execution_context.json from inputs and selected_task_batch."
    )
    parser.add_argument("--inputs", required=True, help="Path to input_payload.json")
    parser.add_argument(
        "--selected-task-batch",
        required=True,
        help="Path to selected_task_batch.json",
    )
    parser.add_argument(
        "--output",
        default="artifacts/coding/execution_context.json",
        help="Path to write execution_context.json",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    inputs = load_json(args.inputs)
    batch = load_json(args.selected_task_batch)

    context = build_execution_context(inputs, batch)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, context)

    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output),
                "feature_id": context.get("feature_id"),
                "selected_checkpoint": context.get("selected_checkpoint"),
                "endpoint_profiles": context.get("endpoint_profiles", []),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
