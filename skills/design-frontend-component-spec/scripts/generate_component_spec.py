#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-frontend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from frontend_design_lib import feature_identity, load_json, slugify, write_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate component_spec.json.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--ui-structure", required=True)
    parser.add_argument("--knowbase-context", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    ui_structure = load_json(args.ui_structure)
    knowbase_context = load_json(args.knowbase_context)
    feature_id, feature_name = feature_identity(final_prd)
    blocks = ui_structure.get("reusable_blocks", []) or ["FeaturePanel"]
    component_rules = [rule["summary"] for rule in knowbase_context.get("component_rules", [])[:4]]
    components = []
    for block in blocks:
        components.append(
            {
                "id": f"component_{slugify(block)}",
                "name": block,
                "props": ["data", "loading", "error"],
                "events": ["onPrimaryAction", "onRetry"],
                "dependencies": ["state_model", "contract_view"],
                "reuse_level": "feature_local" if block != "PageShell" else "shared",
                "constraints": component_rules or ["Keep component responsibilities narrow and declarative."],
            }
        )
    write_json(args.output, {"feature_id": feature_id, "components": components})


if __name__ == "__main__":
    main()
