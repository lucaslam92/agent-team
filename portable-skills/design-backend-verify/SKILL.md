---
name: design.backend.verify
description: >
  Verify that the backend design package is complete enough to enter Coding Mission.
  Use this skill whenever a user asks whether backend design is implementation-ready,
  wants gate results, or needs a structured design_check_report.json.
---

Run the backend design verifiers and emit the final gate report.

Inputs:
- `backend_scope.json`
- `knowbase_context.json`
- `api_contract.yaml`
- `domain_model.json`
- `flow_model.json`
- `storage_plan.json`
- `quality_plan.json`
- `risk_register.json`
- `backend_task_graph.json`

Outputs:
- `artifacts/design/backend/design_check_report.json`

Do this:
1. Check scope, contract, domain, knowbase alignment, operability, and task executability.
2. Summarize gate results and repair actions.
3. Keep the output aligned with [`design_check_report.schema.json`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/design_check_report.schema.json).

Use the helper script:

```bash
python skills/design-backend-verify/scripts/verify_backend_design.py \
  --backend-scope artifacts/design/backend/backend_scope.json \
  --knowbase-context artifacts/design/backend/knowbase_context.json \
  --api-contract artifacts/design/backend/api_contract.yaml \
  --domain-model artifacts/design/backend/domain_model.json \
  --flow-model artifacts/design/backend/flow_model.json \
  --storage-plan artifacts/design/backend/storage_plan.json \
  --quality-plan artifacts/design/backend/quality_plan.json \
  --risk-register artifacts/design/backend/risk_register.json \
  --backend-task-graph artifacts/design/backend/backend_task_graph.json \
  --output artifacts/design/backend/design_check_report.json
```
