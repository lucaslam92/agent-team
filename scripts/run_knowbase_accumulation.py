#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_SOURCE_DIRS = [
    "docs",
    "knowledge",
    "artifacts",
    "src",
    "backend",
    "android",
    "ios",
    "web",
    "api",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def discover_sources(workspace_root: Path, explicit_sources: list[str]) -> list[Path]:
    if explicit_sources:
        return [Path(item).expanduser().resolve() for item in explicit_sources]

    discovered = []
    for rel in DEFAULT_SOURCE_DIRS:
        path = (workspace_root / rel).resolve()
        if path.exists():
            discovered.append(path)
    return discovered


def run_json_command(args: list[str]) -> dict:
    completed = subprocess.run(args, check=True, capture_output=True, text=True)
    stdout = completed.stdout.strip()
    if not stdout:
        return {}
    return json.loads(stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--knowledge-root", default="semantic-store")
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--git-diff-only", action="store_true")
    parser.add_argument("--git-base", default=None)
    parser.add_argument("--git-head", default=None)
    parser.add_argument("--pr-metadata", action="append", default=[])
    parser.add_argument("--review-decisions", default=None)
    parser.add_argument("--skip-promote", action="store_true")
    parser.add_argument("--skip-index-refresh", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root).resolve()
    knowledge_root = Path(args.knowledge_root).expanduser().resolve()
    report_path = Path(args.output).resolve() if args.output else (knowledge_root / "state" / "latest_accumulation_run.json")

    sources = discover_sources(workspace_root, args.source)
    collector_report = knowledge_root / "generated" / "inbox" / "latest-collector-report.json"
    promoter_report = knowledge_root / "generated" / "merge-reports" / "latest-promoter-report.json"
    index_report = knowledge_root / "index" / "latest-rebuild-report.json"

    root = repo_root()
    collector_script = root / "skills" / "knowledge-collector" / "scripts" / "collect_knowledge.py"
    promoter_script = root / "skills" / "knowledge-promoter" / "scripts" / "promote_knowledge.py"
    rebuild_index_script = root / "skills" / "knowledge-promoter" / "scripts" / "rebuild_semantic_index.py"

    collector_cmd = [
        sys.executable,
        str(collector_script),
        "--workspace-root",
        str(workspace_root),
        "--knowledge-root",
        str(knowledge_root),
        "--output",
        str(collector_report),
    ]
    for source in sources:
        collector_cmd.extend(["--source", str(source)])
    if args.git_diff_only:
        collector_cmd.append("--git-diff-only")
    if args.git_base:
        collector_cmd.extend(["--git-base", args.git_base])
    if args.git_head:
        collector_cmd.extend(["--git-head", args.git_head])
    for path in args.pr_metadata:
        collector_cmd.extend(["--pr-metadata", str(Path(path).expanduser().resolve())])

    subprocess.run(collector_cmd, check=True)
    collector_payload = json.loads(collector_report.read_text(encoding="utf-8"))

    promoter_payload = None
    if not args.skip_promote:
        promoter_cmd = [
            sys.executable,
            str(promoter_script),
            "--knowledge-root",
            str(knowledge_root),
            "--output",
            str(promoter_report),
        ]
        if args.review_decisions:
            promoter_cmd.extend(["--review-decisions", str(Path(args.review_decisions).expanduser().resolve())])
        subprocess.run(promoter_cmd, check=True)
        promoter_payload = json.loads(promoter_report.read_text(encoding="utf-8"))

    index_payload = None
    if not args.skip_index_refresh:
        subprocess.run(
            [
                sys.executable,
                str(rebuild_index_script),
                "--knowledge-root",
                str(knowledge_root),
                "--report",
                str(index_report),
            ],
            check=True,
        )
        index_payload = json.loads(index_report.read_text(encoding="utf-8"))

    summary = {
        "workspace_root": str(workspace_root),
        "knowledge_root": str(knowledge_root),
        "sources": [str(item) for item in sources],
        "collector_report_path": str(collector_report),
        "promoter_report_path": str(promoter_report) if promoter_payload is not None else None,
        "index_report_path": str(index_report) if index_payload is not None else None,
        "collector": collector_payload,
        "promoter": promoter_payload,
        "index_refresh": index_payload,
    }
    write_json(report_path, summary)
    print(json.dumps({"status": "completed", "report_path": str(report_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
