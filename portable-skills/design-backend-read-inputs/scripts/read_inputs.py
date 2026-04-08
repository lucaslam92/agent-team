#!/usr/bin/env python3
from __future__ import annotations

import argparse

from backend_design_lib import (
    feature_identity,
    load_json,
    merge_repo_context,
    missing_repo_fields,
    needs_api_specs,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize backend design inputs.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--repo-context", required=True)
    parser.add_argument("--service-inventory")
    parser.add_argument("--architecture-constraints")
    parser.add_argument("--existing-api-specs-dir")
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    repo_context = load_json(args.repo_context)
    service_inventory = load_json(args.service_inventory) if args.service_inventory else None
    architecture_constraints = load_json(args.architecture_constraints) if args.architecture_constraints else None

    merged = merge_repo_context(
        repo_context=repo_context,
        service_inventory=service_inventory,
        architecture_constraints=architecture_constraints,
        existing_api_specs_dir=args.existing_api_specs_dir,
    )

    feature_id, feature_name = feature_identity(final_prd)
    missing = missing_repo_fields(merged)
    warnings: list[str] = []
    status = "ready"
    if missing:
        status = "blocked"
    elif needs_api_specs(final_prd) and not merged.get("existing_apis"):
        status = "degraded"
        warnings.append("No existing API specs were discovered for an API-changing feature.")

    payload = {
        "version": "1.0",
        "feature_id": feature_id,
        "feature_name": feature_name,
        "status": status,
        "final_prd_source": args.final_prd,
        "repo_context_sources": [
            path
            for path in [
                args.repo_context,
                args.service_inventory,
                args.architecture_constraints,
                args.existing_api_specs_dir,
            ]
            if path
        ],
        "repo_context": merged,
        "missing_fields": missing,
        "warnings": warnings,
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
