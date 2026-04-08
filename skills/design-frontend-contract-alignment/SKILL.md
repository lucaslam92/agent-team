---
name: design.frontend.contract_alignment
description: >
  Generate the frontend-facing contract view that coding and verification will consume.
  Use this skill whenever a user asks how frontend should consume backend APIs/events,
  or how to build a fallback contract when backend contract is missing.
---

Generate `frontend_contract_view.json`.

Use the script:

```bash
python skills/design-frontend-contract-alignment/scripts/generate_frontend_contract_view.py \
  --final-prd artifacts/prd/final_prd.json \
  --repo-context-snapshot artifacts/design/frontend/repo_context_snapshot.json \
  --frontend-scope artifacts/design/frontend/frontend_scope.json \
  --api-contract artifacts/design/backend/api_contract.yaml \
  --output artifacts/design/frontend/frontend_contract_view.json
```
