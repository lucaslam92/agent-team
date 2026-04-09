#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_coding_mission import build_coding_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile coding mission final summary from generated artifacts")
    parser.add_argument("--artifacts-dir", default="artifacts/coding")
    return parser


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run() -> int:
    args = build_parser().parse_args()
    root = Path(args.artifacts_dir)
    selected_batch = load(root / "selected_task_batch.json")
    changed_files = load(root / "changed_files.json")
    check_report = load(root / "coding_check_report.json")
    handoff = load(root / "verification_handoff.json")
    summary = build_coding_summary(selected_batch, changed_files, check_report, handoff)
    out = root / "coding_summary.md"
    out.write_text(summary, encoding="utf-8")
    print(json.dumps({"status": "ok", "output": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
