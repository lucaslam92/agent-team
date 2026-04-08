---
name: design.frontend.data_binding
description: >
  Generate the frontend data binding plan before implementation starts.
  Use this skill whenever a user asks how frontend should map requests, responses,
  errors, cache, and async refresh behavior to UI state.
---

Generate `data_binding_plan.json`.

Use the script:

```bash
python skills/design-frontend-data-binding/scripts/generate_data_binding_plan.py \
  --final-prd artifacts/prd/final_prd.json \
  --contract-view artifacts/design/frontend/frontend_contract_view.json \
  --state-model artifacts/design/frontend/state_model.json \
  --output artifacts/design/frontend/data_binding_plan.json
```
