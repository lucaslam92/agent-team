---
name: design.frontend.interaction_design
description: >
  Generate frontend interaction behavior before coding starts.
  Use this skill whenever a user asks for interaction design, validation behavior,
  loading/error handling, retry patterns, or degraded UX behavior.
---

Generate `interaction_spec.json`.

Use the script:

```bash
python skills/design-frontend-interaction-design/scripts/generate_interaction_spec.py \
  --final-prd artifacts/prd/final_prd.json \
  --contract-view artifacts/design/frontend/frontend_contract_view.json \
  --output artifacts/design/frontend/interaction_spec.json
```
