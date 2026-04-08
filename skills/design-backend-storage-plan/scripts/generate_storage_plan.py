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
    load_repo_context_snapshot,
    slugify,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate backend storage_plan.json.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--repo-context-snapshot", required=True)
    parser.add_argument("--knowbase-context", required=True)
    parser.add_argument("--domain-model", required=True)
    parser.add_argument("--flow-model", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    repo_context = load_repo_context_snapshot(args.repo_context_snapshot)
    knowbase_context = load_json(args.knowbase_context)
    domain_model = load_json(args.domain_model)
    flow_model = load_json(args.flow_model)
    feature_id, feature_name = feature_identity(final_prd)
    base_slug = slugify(feature_name)

    entity_names = [entity["name"] for entity in domain_model.get("entities", [])]
    tables = [
        {
            "name": f"{slugify(name)}s",
            "purpose": f"Persist {name} aggregate state.",
            "writes_from": [flow["id"] for flow in flow_model.get("main_flows", [])],
        }
        for name in entity_names
    ] or [
        {
            "name": f"{base_slug}_records",
            "purpose": f"Persist {feature_name} workflow state.",
            "writes_from": ["main_flow"],
        }
    ]
    indexes = [{"table": table["name"], "columns": ["id", "status"], "unique": False} for table in tables]
    cache = [{"name": item, "kind": "cache", "purpose": "Serve read-heavy lookups."} for item in knowbase_context.get("technical_stack", {}).get("cache", [])]
    topics = [{"name": item, "kind": "topic", "purpose": "Carry async state propagation."} for item in knowbase_context.get("technical_stack", {}).get("mq", [])]
    dependencies = [
        {"name": dep.get("name", "unknown_dependency"), "kind": "external_dependency", "purpose": dep.get("summary", "Existing repo dependency.")}
        for dep in repo_context.get("dependencies", [])
    ]
    payload = {
        "feature_id": feature_id,
        "tables": tables,
        "indexes": indexes,
        "cache": cache,
        "topics": topics,
        "external_dependencies": dependencies,
        "migration_plan": [
            f"Create or update tables for {feature_name}.",
            "Backfill nullable fields before enabling write path if needed.",
        ],
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
