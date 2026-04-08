---
name: design.backend.read_knowbase_context
description: >
  Resolve backend-specific knowbase context before API, domain, storage, or quality design starts.
  Use this skill whenever a user needs backend rules, stack constraints, architecture guidance,
  or repo-local overlays compiled into one backend design context.
---

Generate a backend-only `knowbase_context.json` instead of letting each design skill scan raw docs.

Inputs:
- `final_prd.json`
- `knowledge/`
- Repo-local overlay under `knowledge/` when present

Outputs:
- Recommended: `artifacts/design/backend/knowbase_context.json`

Do this:
1. Read only the backend-relevant sources from `knowledge/` and local overlays.
2. Map extracted notes onto the fixed schema in [`knowbase_context.schema.json`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/knowbase_context.schema.json).
3. Separate `ready`, `degraded`, and `blocked` outcomes.
4. Record `resolved_references` and `unresolved_gaps`.
5. Pass only the structured `knowbase_context.json` to downstream backend skills.

Use the helper script:

```bash
python skills/design-backend-read-knowbase-context/scripts/read_knowbase_context.py \
  --final-prd artifacts/prd/final_prd.json \
  --knowledge-root knowledge \
  --repo-overlay-root knowledge \
  --output artifacts/design/backend/knowbase_context.json
```
