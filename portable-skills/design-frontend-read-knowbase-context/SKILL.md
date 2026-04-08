---
name: design.frontend.read_knowbase_context
description: >
  Resolve frontend-specific knowbase context before page, state, contract, or component design starts.
  Use this skill whenever a user needs frontend rules, accessibility constraints,
  stack guidance, or component rules compiled into one frontend design context.
---

Read only the frontend-relevant parts of `knowledge/` and emit `knowbase_context.json`.

Use the script:

```bash
python skills/design-frontend-read-knowbase-context/scripts/read_knowbase_context.py \
  --final-prd artifacts/prd/final_prd.json \
  --knowledge-root knowledge \
  --platform web \
  --repo-overlay-root knowledge \
  --output artifacts/design/frontend/knowbase_context.json
```
