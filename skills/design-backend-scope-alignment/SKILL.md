---
name: design.backend.scope_alignment
description: >
  Lock backend responsibilities, frontend responsibilities, and shared contracts before backend design expands.
  Use this skill whenever a user asks what the backend owns, what stays in frontend,
  or how to freeze backend scope before API and domain design.
---

Generate `backend_scope.json` as the boundary contract for the rest of Backend Design Mission.

Inputs:
- `final_prd.json`
- `repo_context_snapshot.json`
- `knowbase_context.json`

Outputs:
- `artifacts/design/backend/backend_scope.json`

Do this:
1. Translate the feature contract into backend responsibilities.
2. Separate frontend responsibilities and shared contracts.
3. Record out-of-scope items, assumptions, and open issues.
4. Keep the result aligned with [`backend_scope.schema.json`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/backend_scope.schema.json).

Use the helper script:

```bash
python skills/design-backend-scope-alignment/scripts/generate_scope.py \
  --final-prd artifacts/prd/final_prd.json \
  --repo-context-snapshot artifacts/design/backend/repo_context_snapshot.json \
  --knowbase-context artifacts/design/backend/knowbase_context.json \
  --output artifacts/design/backend/backend_scope.json
```
