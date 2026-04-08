---
name: design.frontend.state_model
description: >
  Generate the frontend state model before components and pages are implemented.
  Use this skill whenever a user asks for frontend state design, view state transitions,
  or how server state and local UI state should be organized.
---

Generate `state_model.json`.

Use the script:

```bash
python skills/design-frontend-state-model/scripts/generate_state_model.py \
  --final-prd artifacts/prd/final_prd.json \
  --contract-view artifacts/design/frontend/frontend_contract_view.json \
  --page-map artifacts/design/frontend/page_map.json \
  --output artifacts/design/frontend/state_model.json
```
