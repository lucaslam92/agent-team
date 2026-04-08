---
name: design.frontend.scope_alignment
description: >
  Lock frontend responsibilities and frontend-backend boundaries before deeper frontend design expands.
  Use this skill whenever a user asks what the frontend owns, what stays in backend,
  or how to freeze scope before page and state design.
---

Generate `frontend_scope.json`.

Use the script:

```bash
python skills/design-frontend-scope-alignment/scripts/generate_scope.py \
  --final-prd artifacts/prd/final_prd.json \
  --repo-context-snapshot artifacts/design/frontend/repo_context_snapshot.json \
  --knowbase-context artifacts/design/frontend/knowbase_context.json \
  --output artifacts/design/frontend/frontend_scope.json
```
