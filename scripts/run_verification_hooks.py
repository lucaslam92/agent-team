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
    parser = argparse.ArgumentParser(description="Run coding task verification hooks and write hook results.")
    parser.add_argument("--selected-task-batch", required=True, help="Path to selected_task_batch.json")
    parser.add_argument("--output", required=True, help="Path to write hook_results json")
    parser.add_argument("--execute", action="store_true", help="Execute hooks; otherwise record planned-only status")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    batch = json.loads(Path(args.selected_task_batch).read_text(encoding="utf-8"))
    hook_results = run_task_hooks(batch.get("selected_tasks", []), execute_hooks=args.execute)
    payload = {"hook_results": hook_results, "count": len(hook_results)}
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "output": args.output, "count": len(hook_results)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
