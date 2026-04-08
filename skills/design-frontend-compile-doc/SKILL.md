---
name: design.frontend.compile_doc
description: >
  Compile machine-readable frontend design assets into the final design doc and coding task graph.
  Use this skill whenever a user wants the final frontend design package,
  frontend task graph, or the bridge from design to coding.
---

Generate `frontend_design.md`, `frontend_task_graph.json`, and `design_context_snapshot.json`.

Use the script:

```bash
python skills/design-frontend-compile-doc/scripts/compile_frontend_design.py \
  --final-prd artifacts/prd/final_prd.json \
  --repo-context-snapshot artifacts/design/frontend/repo_context_snapshot.json \
  --knowbase-context artifacts/design/frontend/knowbase_context.json \
  --frontend-scope artifacts/design/frontend/frontend_scope.json \
  --contract-view artifacts/design/frontend/frontend_contract_view.json \
  --page-map artifacts/design/frontend/page_map.json \
  --navigation-map artifacts/design/frontend/navigation_map.json \
  --ui-structure artifacts/design/frontend/ui_structure.json \
  --state-model artifacts/design/frontend/state_model.json \
  --component-spec artifacts/design/frontend/component_spec.json \
  --interaction-spec artifacts/design/frontend/interaction_spec.json \
  --data-binding-plan artifacts/design/frontend/data_binding_plan.json \
  --quality-plan artifacts/design/frontend/quality_plan.json \
  --risk-register artifacts/design/frontend/risk_register.json \
  --doc-output artifacts/design/frontend/frontend_design.md \
  --task-graph-output artifacts/design/frontend/frontend_task_graph.json \
  --context-snapshot-output artifacts/design/frontend/design_context_snapshot.json
```
