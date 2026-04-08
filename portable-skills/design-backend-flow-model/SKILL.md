---
name: design.backend.flow_model
description: >
  Generate backend main flows, error flows, retry flows, and compensation flows before coding starts.
  Use this skill whenever a user asks for backend workflow design, async recovery paths,
  or explicit handling of error and compensation behavior.
---

Generate `flow_model.json` for the backend feature.

Inputs:
- `final_prd.json`
- `api_contract.yaml`

Outputs:
- `artifacts/design/backend/flow_model.json`

Do this:
1. Define the main backend flow.
2. Add explicit error, retry, and compensation flows when the feature needs them.
3. Keep each flow tied to acceptance criteria.
4. Keep the result aligned with [`flow_model.schema.json`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/flow_model.schema.json).

Use the helper script:

```bash
python skills/design-backend-flow-model/scripts/generate_flow_model.py \
  --final-prd artifacts/prd/final_prd.json \
  --api-contract artifacts/design/backend/api_contract.yaml \
  --output artifacts/design/backend/flow_model.json
```
