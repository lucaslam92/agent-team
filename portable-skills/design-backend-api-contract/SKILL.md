---
name: design.backend.api_contract
description: >
  Generate the backend API, event, and job contract that coding and verification will consume.
  Use this skill whenever a user asks for backend API design, endpoint/event/job contracts,
  or the machine-readable contract that bridges design to implementation.
---

Generate `api_contract.yaml` as the central backend design artifact.

Inputs:
- `final_prd.json`
- `repo_context_snapshot.json`
- `backend_scope.json`
- `knowbase_context.json`

Outputs:
- `artifacts/design/backend/api_contract.yaml`

Do this:
1. Build contract entries for APIs, events, and jobs from backend scope and acceptance criteria.
2. Keep global conventions aligned with knowbase API rules.
3. Emit verification mapping for downstream test and verification work.
4. Keep the result aligned with [`api_contract.schema.yaml`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/api_contract.schema.yaml).

Use the helper script:

```bash
python skills/design-backend-api-contract/scripts/generate_api_contract.py \
  --final-prd artifacts/prd/final_prd.json \
  --repo-context-snapshot artifacts/design/backend/repo_context_snapshot.json \
  --backend-scope artifacts/design/backend/backend_scope.json \
  --knowbase-context artifacts/design/backend/knowbase_context.json \
  --output artifacts/design/backend/api_contract.yaml
```
