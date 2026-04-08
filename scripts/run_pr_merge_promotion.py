#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def git_output(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def detect_merge_range(workspace_root: Path) -> tuple[str, str, str]:
    head = git_output(["git", "rev-parse", "HEAD"], workspace_root)
    parents_line = git_output(["git", "rev-list", "--parents", "-n", "1", "HEAD"], workspace_root)
    parts = parents_line.split()

    if len(parts) >= 3:
        return parts[1], head, "head_merge_commit_first_parent"

    try:
        base = git_output(["git", "rev-parse", "HEAD~1"], workspace_root)
        return base, head, "head_single_commit_parent"
    except subprocess.CalledProcessError:
        return head, head, "single_commit_repository"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--knowledge-root", default="semantic-store")
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--git-base", default=None)
    parser.add_argument("--git-head", default="HEAD")
    parser.add_argument("--pr-metadata", action="append", default=[])
    parser.add_argument("--review-decisions", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root).resolve()
    knowledge_root = Path(args.knowledge_root).expanduser().resolve()
    output_path = (
        Path(args.output).resolve()
        if args.output
        else (knowledge_root / "state" / "latest_pr_merge_promotion.json")
    )

    if args.git_base:
        git_base = args.git_base
        git_head = args.git_head
        range_strategy = "explicit"
    else:
        git_base, git_head, range_strategy = detect_merge_range(workspace_root)

    runner = repo_root() / "scripts" / "run_knowbase_accumulation.py"
    command = [
        sys.executable,
        str(runner),
        "--workspace-root",
        str(workspace_root),
        "--knowledge-root",
        str(knowledge_root),
        "--git-base",
        git_base,
        "--git-head",
        git_head,
        "--output",
        str(output_path),
    ]
    for source in args.source:
        command.extend(["--source", str(Path(source).expanduser().resolve())])
    for path in args.pr_metadata:
        command.extend(["--pr-metadata", str(Path(path).expanduser().resolve())])
    if args.review_decisions:
        command.extend(["--review-decisions", str(Path(args.review_decisions).expanduser().resolve())])

    summary = {
        "mode": "manual_pr_merge_promotion",
        "workspace_root": str(workspace_root),
        "knowledge_root": str(knowledge_root),
        "git_base": git_base,
        "git_head": git_head,
        "range_strategy": range_strategy,
        "sources": args.source,
        "pr_metadata": args.pr_metadata,
        "review_decisions": args.review_decisions,
        "output_path": str(output_path),
        "command": command,
    }

    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    subprocess.run(command, check=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
