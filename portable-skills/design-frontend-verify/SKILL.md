---
name: design.frontend.verify
description: >
  Verify that the frontend design package is complete enough to enter Coding Mission.
  Use this skill whenever a user asks whether frontend design is implementation-ready,
  wants gate results, or needs a structured design_check_report.json.
---

Generate `design_check_report.json`.

When a gate fails, the report should include analyzer repair plans with executable command suggestions.

Use the script:

```bash
python skills/design-frontend-verify/scripts/verify_frontend_design.py \
  --frontend-scope artifacts/design/frontend/frontend_scope.json \
  --knowbase-context artifacts/design/frontend/knowbase_context.json \
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
  --frontend-task-graph artifacts/design/frontend/frontend_task_graph.json \
  --output artifacts/design/frontend/design_check_report.json

python scripts/run_design_repair.py \
  --report artifacts/design/frontend/design_check_report.json
```
