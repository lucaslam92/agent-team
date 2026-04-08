#!/usr/bin/env python3
from __future__ import annotations

import argparse

from frontend_design_lib import feature_identity, load_json, merge_repo_context, missing_repo_fields, needs_contract, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize frontend design inputs.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--repo-context", required=True)
    parser.add_argument("--ui-inventory")
    parser.add_argument("--existing-routes")
    parser.add_argument("--frontend-architecture-constraints")
    parser.add_argument("--api-contract")
    parser.add_argument("--figma-context")
    parser.add_argument("--design-tokens")
    parser.add_argument("--output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    repo_context = load_json(args.repo_context)
    ui_inventory = load_json(args.ui_inventory) if args.ui_inventory else None
    existing_routes = load_json(args.existing_routes) if args.existing_routes else None
    constraints = load_json(args.frontend_architecture_constraints) if args.frontend_architecture_constraints else None
    merged = merge_repo_context(repo_context, ui_inventory, existing_routes, constraints)
    feature_id, feature_name = feature_identity(final_prd)
    missing = missing_repo_fields(merged)
    warnings: list[str] = []
    status = "ready"
    if missing:
        status = "blocked"
    elif needs_contract(final_prd) and not args.api_contract:
        status = "degraded"
        warnings.append("Frontend feature appears to consume backend behavior but api_contract.yaml was not provided.")
    payload = {
        "version": "1.0",
        "feature_id": feature_id,
        "feature_name": feature_name,
        "status": status,
        "final_prd_source": args.final_prd,
        "repo_context_sources": [path for path in [args.repo_context, args.ui_inventory, args.existing_routes, args.frontend_architecture_constraints] if path],
        "repo_context": merged,
        "optional_inputs": {
            "api_contract": args.api_contract,
            "figma_context": args.figma_context,
            "design_tokens": args.design_tokens,
        },
        "missing_fields": missing,
        "warnings": warnings,
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
