---
name: design.frontend.read_inputs
description: >
  Normalize frontend design inputs and stop early when repo context is incomplete.
  Use this skill whenever a user wants to start frontend design, scope a frontend feature,
  or turn final_prd plus repo context into implementation-ready frontend assets.
---

Normalize `final_prd`, repo context, and optional frontend inputs into one gated snapshot.

Use the script:

```bash
python skills/design-frontend-read-inputs/scripts/read_inputs.py \
  --final-prd artifacts/prd/final_prd.json \
  --repo-context repo_context.json \
  --ui-inventory ui_inventory.json \
  --existing-routes existing_routes.json \
  --frontend-architecture-constraints frontend_architecture_constraints.json \
  --api-contract artifacts/design/backend/api_contract.yaml \
  --figma-context figma_context.json \
  --design-tokens design_tokens.json \
  --output artifacts/design/frontend/repo_context_snapshot.json
```
