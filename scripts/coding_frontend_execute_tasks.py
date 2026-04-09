#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_coding_mission import run_task_hooks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute frontend tasks from selected_task_batch.json")
    parser.add_argument("--selected-task-batch", required=True)
    parser.add_argument("--output", default="artifacts/coding/frontend_task_execution.json")
    parser.add_argument("--execute-hooks", action="store_true")
    return parser


def run() -> int:
    args = build_parser().parse_args()
    batch = json.loads(Path(args.selected_task_batch).read_text(encoding="utf-8"))
    # Explicitly match known frontend endpoint prefixes.
    # Avoid "not startswith backend" — it would incorrectly capture empty or cross endpoints.
    FRONTEND_PREFIXES = ("frontend", "web", "mobile", "ios", "android")
    selected = [
        task for task in batch.get("selected_tasks", [])
        if str(task.get("endpoint", "")).lower().startswith(FRONTEND_PREFIXES)
    ]
    hook_results = run_task_hooks(selected, execute_hooks=args.execute_hooks)
    payload = {
        "endpoint": "frontend",
        "task_count": len(selected),
        "hook_results": hook_results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "output": str(output), "task_count": len(selected)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
