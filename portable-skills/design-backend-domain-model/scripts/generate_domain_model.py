#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-backend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from backend_design_lib import (  # noqa: E402
    feature_identity,
    load_json,
    slugify,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate backend domain_model.json.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--backend-scope", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    scope = load_json(args.backend_scope)
    feature_id, feature_name = feature_identity(final_prd)
    entity_name = "".join(part.capitalize() for part in slugify(feature_name).split("_"))
    payload = {
        "feature_id": feature_id,
        "entities": [
            {
                "name": entity_name,
                "summary": f"Primary domain entity for {feature_name}.",
                "fields": [
                    {"name": "id", "type": "string", "required": True},
                    {"name": "status", "type": "string", "required": True},
                ],
            }
        ],
        "value_objects": [
            {
                "name": f"{entity_name}Context",
                "summary": "Value object that captures request-scoped metadata.",
                "fields": [
                    {"name": "actor_id", "type": "string", "required": True},
                    {"name": "request_id", "type": "string", "required": True},
                ],
            }
        ],
        "aggregates": [
            {
                "name": f"{entity_name}Aggregate",
                "root": entity_name,
                "members": [f"{entity_name}Context"],
            }
        ],
        "state_machines": [
            {
                "name": f"{entity_name}Lifecycle",
                "states": ["draft", "active", "failed"],
                "transitions": [
                    {"from": "draft", "to": "active", "trigger": "commit_success"},
                    {"from": "active", "to": "failed", "trigger": "compensation_required"},
                ],
            }
        ],
        "invariants": [
            "Every accepted write must produce a deterministic state transition.",
            f"Scope assumptions count: {len(scope.get('assumptions', []))}.",
        ],
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
