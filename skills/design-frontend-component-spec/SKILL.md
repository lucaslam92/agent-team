---
name: design.frontend.component_spec
description: >
  Generate the frontend component contract and reuse plan before coding starts.
  Use this skill whenever a user asks for component breakdown, reusable blocks,
  component constraints, or page-to-component decomposition.
---

Generate `component_spec.json`.

Use the script:

```bash
python skills/design-frontend-component-spec/scripts/generate_component_spec.py \
  --final-prd artifacts/prd/final_prd.json \
  --ui-structure artifacts/design/frontend/ui_structure.json \
  --knowbase-context artifacts/design/frontend/knowbase_context.json \
  --output artifacts/design/frontend/component_spec.json
```
