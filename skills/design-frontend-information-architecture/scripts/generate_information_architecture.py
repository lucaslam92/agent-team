#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-frontend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from frontend_design_lib import acceptance_items, feature_identity, load_json, slugify, write_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate page_map.json, navigation_map.json, and ui_structure.json.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--repo-context-snapshot", required=True)
    parser.add_argument("--frontend-scope", required=True)
    parser.add_argument("--contract-view", required=True)
    parser.add_argument("--page-map-output", required=True)
    parser.add_argument("--navigation-map-output", required=True)
    parser.add_argument("--ui-structure-output", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    repo_context = load_json(args.repo_context_snapshot).get("repo_context", {})
    contract_view = load_json(args.contract_view)
    feature_id, feature_name = feature_identity(final_prd)
    acceptance = acceptance_items(final_prd)
    page_id = f"page_{slugify(feature_name)}"
    page_map = {
        "feature_id": feature_id,
        "pages": [{"id": page_id, "name": f"{feature_name} Page", "summary": "Primary feature surface."}],
        "entry_points": [route.get("path", "/") for route in repo_context.get("routes", [])[:1]] or ["/"],
        "page_goals": [{"page_id": page_id, "goal": item["summary"]} for item in acceptance],
        "acceptance_refs": [item["ref"] for item in acceptance],
    }
    navigation_map = {
        "feature_id": feature_id,
        "routes": [{"id": f"route_{page_id}", "path": page_map["entry_points"][0], "page_id": page_id}],
        "transitions": [{"from": "entry", "to": page_id, "trigger": "open_feature"}],
        "guards": ["Require expected auth/session before entering protected page."],
        "params": ["feature_id"],
        "deeplink_rules": ["Deeplink should restore page state from URL-safe params when possible."],
    }
    ui_structure = {
        "feature_id": feature_id,
        "page_sections": [{"page_id": page_id, "sections": ["header", "content", "feedback"]}],
        "component_tree": [{"page_id": page_id, "nodes": ["PageShell", "FeatureForm", "ResultPanel"]}],
        "reusable_blocks": ["PageShell", "FeedbackBanner"],
        "empty_loading_error_states": ["empty_state", "loading_state", "error_state"] + (["async_refresh_state"] if contract_view.get("consumed_events") else []),
    }
    write_json(args.page_map_output, page_map)
    write_json(args.navigation_map_output, navigation_map)
    write_json(args.ui_structure_output, ui_structure)


if __name__ == "__main__":
    main()
