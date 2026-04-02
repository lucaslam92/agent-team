#!/usr/bin/env python3
"""
Android Auto Dev Harness — CLI entry point.

Usage:
    python -m aadh.main --task "给设置页新增清除缓存入口，点击后弹确认框，确认后显示成功提示"

    python -m aadh.main \\
        --task "Add a dark mode toggle to Settings" \\
        --project-path /path/to/my-android-app \\
        --settings /path/to/settings.yaml \\
        --iterations 5 \\
        --threshold 8.0
"""

from __future__ import annotations
import argparse
import sys
import os
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def merge_cli_overrides(settings: dict, args: argparse.Namespace) -> dict:
    """Apply CLI flags on top of settings.yaml values."""
    if args.project_path:
        settings["project"]["path"] = args.project_path
    if args.iterations:
        settings["harness"]["max_iterations"] = args.iterations
    if args.threshold:
        settings["harness"]["pass_threshold"] = args.threshold
    if args.artifacts_dir:
        settings["harness"]["artifacts_dir"] = args.artifacts_dir
    return settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Android Auto Dev Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--task",         required=True,  help="Natural-language task description")
    parser.add_argument("--project-path", default=None,   help="Android project root (overrides settings.yaml)")
    parser.add_argument("--settings",     default=None,   help="Path to settings.yaml (default: aadh/config/settings.yaml)")
    parser.add_argument("--commands",     default=None,   help="Path to commands.yaml")
    parser.add_argument("--iterations",   type=int,        default=None, help="Max iterations (overrides settings)")
    parser.add_argument("--threshold",    type=float,      default=None, help="Pass score threshold 0-10 (overrides settings)")
    parser.add_argument("--artifacts-dir",default=None,   help="Where to write run artifacts")
    parser.add_argument("--quiet",        action="store_true", help="Suppress progress output")
    args = parser.parse_args()

    # ── Load config ───────────────────────────────────────────────────────────
    config_dir = Path(__file__).parent / "config"

    settings_path = Path(args.settings) if args.settings else config_dir / "settings.yaml"
    commands_path = Path(args.commands) if args.commands else config_dir / "commands.yaml"

    if not settings_path.exists():
        print(f"Error: settings file not found: {settings_path}", file=sys.stderr)
        print("Copy aadh/config/settings.yaml to your project and edit it.", file=sys.stderr)
        sys.exit(1)

    settings = load_yaml(settings_path)
    commands = load_yaml(commands_path)
    settings = merge_cli_overrides(settings, args)

    # ── Validate API key presence ─────────────────────────────────────────────
    default_llm = settings.get("llm", {}).get("default", {})
    env_key = default_llm.get("api_key_env", "ANTHROPIC_API_KEY")
    if not os.environ.get(env_key) and not default_llm.get("api_key"):
        print(f"Error: {env_key} environment variable not set.", file=sys.stderr)
        sys.exit(1)

    # ── Run ───────────────────────────────────────────────────────────────────
    from aadh.core.orchestrator import run

    report = run(
        task=args.task,
        settings=settings,
        commands=commands,
        verbose=not args.quiet,
    )

    # Exit code reflects pass/fail for CI usage
    sys.exit(0 if report.status.value == "success" else 1)


if __name__ == "__main__":
    main()
