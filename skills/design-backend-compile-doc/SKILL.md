---
name: design.backend.compile_doc
description: >
  Compile machine-readable backend design assets into the human-readable design doc and coding task graph.
  Use this skill whenever a user wants the final backend design package, backend task graph,
  or the design-to-coding bridge artifact.
---

Generate the compiled backend design outputs after the contract, models, storage plan, and quality plan exist.

Inputs:
- `final_prd.json`
- `repo_context_snapshot.json`
- `knowbase_context.json`
- `backend_scope.json`
- `api_contract.yaml`
- `domain_model.json`
- `flow_model.json`
- `storage_plan.json`
- `quality_plan.json`
- `risk_register.json`

Outputs:
- `artifacts/design/backend/backend_design.md`
- `artifacts/design/backend/backend_task_graph.json`
- `artifacts/design/backend/design_context_snapshot.json`

Do this:
1. Compile the design summary for human review.
2. Generate the coding-ready task graph with observable completion criteria.
3. Snapshot the design basis and key constraints.
4. Keep outputs aligned with [`backend_task_graph.schema.json`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/backend_task_graph.schema.json) and [`design_context_snapshot.schema.json`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/design_context_snapshot.schema.json).

Use the helper script:

```bash
python skills/design-backend-compile-doc/scripts/compile_backend_design.py \
  --final-prd artifacts/prd/final_prd.json \
  --repo-context-snapshot artifacts/design/backend/repo_context_snapshot.json \
  --knowbase-context artifacts/design/backend/knowbase_context.json \
  --backend-scope artifacts/design/backend/backend_scope.json \
  --api-contract artifacts/design/backend/api_contract.yaml \
  --domain-model artifacts/design/backend/domain_model.json \
  --flow-model artifacts/design/backend/flow_model.json \
  --storage-plan artifacts/design/backend/storage_plan.json \
  --quality-plan artifacts/design/backend/quality_plan.json \
  --risk-register artifacts/design/backend/risk_register.json \
  --doc-output artifacts/design/backend/backend_design.md \
  --task-graph-output artifacts/design/backend/backend_task_graph.json \
  --context-snapshot-output artifacts/design/backend/design_context_snapshot.json
```
