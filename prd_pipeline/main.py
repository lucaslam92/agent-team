"""
PRD Pipeline — CLI entry point.

Usage:
    # Plain text
    python -m prd_pipeline.main --input "用户可以在设置页清除缓存" --source text

    # Jira ticket (reuses AADH input layer)
    python -m prd_pipeline.main --input "AND-123" --source issue

    # Markdown file
    python -m prd_pipeline.main --input ./requirements/feature.md --source prd

    # With Figma JSON
    python -m prd_pipeline.main --input "..." --figma ./figma_export.json
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

import yaml


def main():
    parser = argparse.ArgumentParser(description="PRD Pipeline")
    parser.add_argument("--input",    required=True,  help="Raw requirement (text, Jira key/URL, .md path, Confluence URL)")
    parser.add_argument("--source",   default="text", choices=["text", "prd", "issue"], help="Input source type hint")
    parser.add_argument("--figma",    default=None,   help="Path to Figma JSON export (optional)")
    parser.add_argument("--settings", default=None,   help="Path to settings.yaml")
    parser.add_argument("--output",   default="./prd_output", help="Output directory for final_prd.json / .md")
    parser.add_argument("--quiet",    action="store_true")
    args = parser.parse_args()

    # Settings — reuse AADH settings.yaml (same LLM config schema)
    settings_path = Path(args.settings) if args.settings else \
                    Path(__file__).parent.parent / "aadh" / "config" / "settings.yaml"
    with open(settings_path, encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    # Figma
    figma_data = None
    if args.figma:
        with open(args.figma, encoding="utf-8") as f:
            figma_data = json.load(f)

    # Validate API key
    llm_default = settings.get("llm", {}).get("default", {})
    env_key = llm_default.get("api_key_env", "ANTHROPIC_API_KEY")
    if not os.environ.get(env_key):
        print(f"Error: {env_key} not set.", file=sys.stderr)
        sys.exit(1)

    # Handle multi-source input (reuse AADH input layer if needed)
    raw_input = args.input
    from aadh.input.parser import detect, InputType
    detected = detect(raw_input)
    if detected != InputType.TEXT:
        input_cfg = settings.get("input", {})
        from aadh.input.parser import parse as parse_input
        spec = parse_input(raw_input, input_cfg)
        raw_input = spec.description
        if not args.quiet:
            print(f"[input] {detected.value}: {spec.title}")

    from prd_pipeline.pipeline import run, PipelineBlocked
    try:
        run(
            raw_input=raw_input,
            source=args.source,
            settings=settings,
            figma_data=figma_data,
            output_dir=Path(args.output),
            verbose=not args.quiet,
        )
    except PipelineBlocked as e:
        print(f"\n⛔ Pipeline stopped at {e.gate}:\n{e.reason}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
