---
name: design.backend.storage_plan
description: >
  Generate the backend storage, cache, topic, dependency, and migration plan for implementation.
  Use this skill whenever a user asks for data design, persistence layout, integration dependencies,
  or the backend storage plan before coding.
---

Generate `storage_plan.json` for the backend feature.

Inputs:
- `final_prd.json`
- `repo_context_snapshot.json`
- `knowbase_context.json`
- `domain_model.json`
- `flow_model.json`

Outputs:
- `artifacts/design/backend/storage_plan.json`

Do this:
1. Translate the domain and flow model into tables, indexes, caches, topics, and dependencies.
2. Record migration expectations early.
3. Keep the result aligned with [`storage_plan.schema.json`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/storage_plan.schema.json).

Use the helper script:

```bash
python skills/design-backend-storage-plan/scripts/generate_storage_plan.py \
  --final-prd artifacts/prd/final_prd.json \
  --repo-context-snapshot artifacts/design/backend/repo_context_snapshot.json \
  --knowbase-context artifacts/design/backend/knowbase_context.json \
  --domain-model artifacts/design/backend/domain_model.json \
  --flow-model artifacts/design/backend/flow_model.json \
  --output artifacts/design/backend/storage_plan.json
```
