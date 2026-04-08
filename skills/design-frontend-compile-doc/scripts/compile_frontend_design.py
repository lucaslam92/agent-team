#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

LIB_DIR = Path(__file__).resolve().parents[2] / "design-frontend-read-inputs" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from frontend_design_lib import acceptance_items, feature_identity, load_json, write_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile frontend design doc, task graph, and context snapshot.")
    parser.add_argument("--final-prd", required=True)
    parser.add_argument("--repo-context-snapshot", required=True)
    parser.add_argument("--knowbase-context", required=True)
    parser.add_argument("--frontend-scope", required=True)
    parser.add_argument("--contract-view", required=True)
    parser.add_argument("--page-map", required=True)
    parser.add_argument("--navigation-map", required=True)
    parser.add_argument("--ui-structure", required=True)
    parser.add_argument("--state-model", required=True)
    parser.add_argument("--component-spec", required=True)
    parser.add_argument("--interaction-spec", required=True)
    parser.add_argument("--data-binding-plan", required=True)
    parser.add_argument("--quality-plan", required=True)
    parser.add_argument("--risk-register", required=True)
    parser.add_argument("--doc-output", required=True)
    parser.add_argument("--task-graph-output", required=True)
    parser.add_argument("--context-snapshot-output", required=True)
    return parser


def write_text(path: str | Path, content: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def build_task_graph(feature_id: str, platform: str, contract_view: dict[str, object], page_map: dict[str, object], component_spec: dict[str, object], risk_register: dict[str, object]) -> dict[str, object]:
    tasks: list[dict[str, object]] = []
    for page in page_map.get("pages", []):
        page_id = page["id"]
        tasks.extend(
            [
                {
                    "id": f"{page_id}_state",
                    "title": f"Implement state for {page_id}",
                    "category": "state",
                    "module": platform,
                    "depends_on": [],
                    "parallel_group": "state",
                    "priority": "high",
                    "from_contract": [],
                    "from_design_artifacts": ["state_model.json"],
                    "acceptance_refs": page_map.get("acceptance_refs", []),
                    "goal": "Establish local and server state wiring for the page.",
                    "files_hint": [],
                    "implementation_notes": ["State should be the dependency root for page rendering."],
                    "done_when": ["Page state transitions handle idle, loading, success, and error."],
                    "verification_hooks": ["compile", "unit_test"],
                    "retryable": False,
                    "blocking": True,
                },
                {
                    "id": f"{page_id}_page",
                    "title": f"Implement page surface for {page_id}",
                    "category": "page",
                    "module": platform,
                    "depends_on": [f"{page_id}_state"],
                    "parallel_group": "page",
                    "priority": "high",
                    "from_contract": [],
                    "from_design_artifacts": ["page_map.json", "ui_structure.json"],
                    "acceptance_refs": page_map.get("acceptance_refs", []),
                    "goal": "Render the feature page and its primary sections.",
                    "files_hint": [],
                    "implementation_notes": ["Keep page layout aligned with ui_structure."],
                    "done_when": ["Primary page renders all required sections."],
                    "verification_hooks": ["compile", "snapshot_test"],
                    "retryable": False,
                    "blocking": True,
                },
                {
                    "id": f"{page_id}_test",
                    "title": f"Test {page_id}",
                    "category": "test",
                    "module": platform,
                    "depends_on": [f"{page_id}_page"],
                    "parallel_group": "test",
                    "priority": "high",
                    "from_contract": [],
                    "from_design_artifacts": ["frontend_task_graph.json"],
                    "acceptance_refs": page_map.get("acceptance_refs", []),
                    "goal": "Verify page behavior against design and acceptance mapping.",
                    "files_hint": [],
                    "implementation_notes": ["Cover core user journey and failure state."],
                    "done_when": ["Automated checks cover the primary page flow."],
                    "verification_hooks": ["unit_test", "integration_test"],
                    "retryable": True,
                    "blocking": False,
                },
            ]
        )
    if contract_view.get("consumed_apis"):
        tasks.append(
            {
                "id": "contract_adapter",
                "title": "Implement frontend contract adapter and request hooks",
                "category": "contract_adapter",
                "module": platform,
                "depends_on": [task["id"] for task in tasks if task["category"] == "state"],
                "parallel_group": "data",
                "priority": "high",
                "from_contract": [api["id"] for api in contract_view.get("consumed_apis", [])],
                "from_design_artifacts": ["frontend_contract_view.json", "data_binding_plan.json"],
                "acceptance_refs": [mapping["acceptance_ref"] for mapping in contract_view.get("acceptance_mapping", [])],
                "goal": "Connect frontend state to backend contract.",
                "files_hint": [],
                "implementation_notes": ["Respect error mapping and retry behavior."],
                "done_when": ["Frontend can request and consume backend responses through a stable adapter."],
                "verification_hooks": ["contract_test", "integration_test"],
                "retryable": True,
                "blocking": True,
            }
        )
    for component in component_spec.get("components", []):
        tasks.append(
            {
                "id": f"{component['id']}_component",
                "title": f"Implement component {component['name']}",
                "category": "component",
                "module": platform,
                "depends_on": [],
                "parallel_group": "component",
                "priority": "medium",
                "from_contract": [],
                "from_design_artifacts": ["component_spec.json"],
                "acceptance_refs": [],
                "goal": "Build reusable frontend component.",
                "files_hint": [],
                "implementation_notes": component.get("constraints", []),
                "done_when": [f"{component['name']} renders its declared props and events."],
                "verification_hooks": ["compile", "snapshot_test"],
                "retryable": False,
                "blocking": False,
            }
        )
    tasks.append(
        {
            "id": "observability_frontend",
            "title": "Add frontend observability and accessibility coverage",
            "category": "observability",
            "module": platform,
            "depends_on": [task["id"] for task in tasks if task["category"] in {"page", "contract_adapter"}],
            "parallel_group": "quality",
            "priority": "medium",
            "from_contract": [],
            "from_design_artifacts": ["quality_plan.json"],
            "acceptance_refs": [],
            "goal": "Add client telemetry and UI quality safeguards.",
            "files_hint": [],
            "implementation_notes": ["Track primary CTA, loading, success, error, and accessibility regressions."],
            "done_when": ["Core UI interactions expose telemetry and quality hooks."],
            "verification_hooks": ["smoke_test", "manual_rule_check"],
            "retryable": True,
            "blocking": False,
        }
    )
    blocking_issues = [risk["summary"] for risk in risk_register.get("risks", []) if risk.get("blocking")]
    return {
        "version": "1.0",
        "feature_id": feature_id,
        "platform": platform,
        "generated_from": [
            "frontend_scope.json",
            "frontend_contract_view.json",
            "page_map.json",
            "navigation_map.json",
            "ui_structure.json",
            "state_model.json",
            "component_spec.json",
            "interaction_spec.json",
            "data_binding_plan.json",
            "quality_plan.json",
            "risk_register.json",
        ],
        "execution_policy": {
            "default_parallelism": "page_and_component_parallelism",
            "notes": ["Keep state before page, and contract adapter before UI paths that depend on remote data."],
        },
        "tasks": tasks,
        "checkpoints": [
            {"id": "cp_shell", "summary": "Page shell and state foundation ready.", "task_ids": [task["id"] for task in tasks[:3]]},
            {"id": "cp_quality", "summary": "Contract, component, and quality work ready.", "task_ids": [task["id"] for task in tasks[3:]]},
        ],
        "final_gate": {
            "ready": not blocking_issues and bool(tasks),
            "required_checks": ["compile", "integration_test", "snapshot_test"],
            "blocking_issues": blocking_issues,
            "notes": ["All blocking frontend design risks must be resolved before coding exit."],
        },
    }


def main() -> None:
    args = build_parser().parse_args()
    final_prd = load_json(args.final_prd)
    repo_snapshot = load_json(args.repo_context_snapshot)
    knowbase_context = load_json(args.knowbase_context)
    frontend_scope = load_json(args.frontend_scope)
    contract_view = load_json(args.contract_view)
    page_map = load_json(args.page_map)
    navigation_map = load_json(args.navigation_map)
    ui_structure = load_json(args.ui_structure)
    state_model = load_json(args.state_model)
    component_spec = load_json(args.component_spec)
    interaction_spec = load_json(args.interaction_spec)
    data_binding_plan = load_json(args.data_binding_plan)
    quality_plan = load_json(args.quality_plan)
    risk_register = load_json(args.risk_register)
    feature_id, feature_name = feature_identity(final_prd)
    platform = repo_snapshot.get("repo_context", {}).get("platform", "web")
    task_graph = build_task_graph(feature_id, platform, contract_view, page_map, component_spec, risk_register)
    write_json(args.task_graph_output, task_graph)
    context_snapshot = {
        "feature_id": feature_id,
        "prd_source": args.final_prd,
        "repo_context_sources": repo_snapshot.get("repo_context_sources", [args.repo_context_snapshot]),
        "knowbase_sources": [ref["path"] for ref in knowbase_context.get("resolved_references", [])],
        "api_contract_source": repo_snapshot.get("optional_inputs", {}).get("api_contract") or "",
        "figma_sources": [repo_snapshot.get("optional_inputs", {}).get("figma_context")] if repo_snapshot.get("optional_inputs", {}).get("figma_context") else [],
        "key_constraints": [note["summary"] for note in knowbase_context.get("architecture_constraints", [])[:6]] + [note["summary"] for note in knowbase_context.get("frontend_rules", [])[:6]],
        "status": "degraded" if knowbase_context.get("extraction_status") == "degraded" else "ready",
    }
    write_json(args.context_snapshot_output, context_snapshot)
    acceptance_refs = [item["ref"] for item in acceptance_items(final_prd)]
    doc = f"""# Frontend Design

## Overview
- Feature: {feature_name}
- Platform: {platform}
- Acceptance refs: {", ".join(acceptance_refs)}

## Design Basis
- final_prd: {args.final_prd}
- repo context: {args.repo_context_snapshot}
- knowbase context: {args.knowbase_context}

## Scope And Responsibilities
- Frontend responsibilities: {len(frontend_scope.get("frontend_responsibilities", []))}
- Shared contracts: {len(frontend_scope.get("shared_contracts", []))}

## Contract Consumption Summary
- Consumed APIs: {len(contract_view.get('consumed_apis', []))}
- Consumed events: {len(contract_view.get('consumed_events', []))}
- Fallback contracts: {len(contract_view.get('fallback_contracts', []))}

## Page And Navigation Summary
- Pages: {len(page_map.get('pages', []))}
- Routes: {len(navigation_map.get('routes', []))}

## UI Structure And Component Summary
- Reusable blocks: {len(ui_structure.get('reusable_blocks', []))}
- Components: {len(component_spec.get('components', []))}

## State Model Summary
- Server state entries: {len(state_model.get('server_state', []))}
- View state entries: {len(state_model.get('view_state', []))}

## Data Binding Summary
- Request bindings: {len(data_binding_plan.get('request_bindings', []))}
- Error mappings: {len(data_binding_plan.get('error_mapping', []))}

## Quality And Performance Plan
- Accessibility: {quality_plan['accessibility']['summary']}
- Performance: {quality_plan['performance_budget']['summary']}

## Risks And Deferred Items
- Risks: {len(risk_register.get('risks', []))}

## Coding Task Breakdown
- Tasks: {len(task_graph.get('tasks', []))}

## Verification Mapping
- Required checks: {", ".join(task_graph['final_gate']['required_checks'])}

## Open Issues
{chr(10).join(f"- {risk['summary']}" for risk in risk_register.get('risks', []) if risk.get('blocking')) or "- None"}
"""
    write_text(args.doc_output, doc)


if __name__ == "__main__":
    main()
