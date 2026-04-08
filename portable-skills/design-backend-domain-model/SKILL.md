---
name: design.backend.domain_model
description: >
  Generate the backend domain model, aggregates, and state machines that coding will implement.
  Use this skill whenever a user asks for backend domain boundaries, business entities,
  state transitions, or implementation-ready backend modeling.
---

Generate `domain_model.json` for the backend feature.

Inputs:
- `final_prd.json`
- `backend_scope.json`

Outputs:
- `artifacts/design/backend/domain_model.json`

Do this:
1. Define entities, value objects, aggregates, and state machines.
2. Record the invariants that backend code must preserve.
3. Keep the result aligned with [`domain_model.schema.json`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/domain_model.schema.json).

Use the helper script:

```bash
python skills/design-backend-domain-model/scripts/generate_domain_model.py \
  --final-prd artifacts/prd/final_prd.json \
  --backend-scope artifacts/design/backend/backend_scope.json \
  --output artifacts/design/backend/domain_model.json
```
