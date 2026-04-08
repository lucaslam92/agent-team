---
name: design.backend.read_inputs
description: >
  Normalize backend design inputs and gate missing repo context before any backend design work.
  Use this skill whenever a user wants to start backend design, scope a backend feature,
  or turn final_prd plus repo context into implementation-ready backend assets.
---

Produce a normalized backend input snapshot before generating any design artifact.

Inputs:
- `final_prd.json`
- `repo_context.json`
- `service_inventory.json` when available
- `architecture_constraints.json` when available
- `existing_api_specs/` when available

Outputs:
- Recommended: `artifacts/design/backend/repo_context_snapshot.json`

Do this:
1. Read and merge repo context inputs into one normalized object.
2. Enforce the minimum required fields from [`repo_context.schema.json`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/repo_context.schema.json).
3. Mark the result `blocked` when critical fields are missing.
4. Mark the result `degraded` when API-changing work has no existing API inventory.
5. Persist the normalized snapshot for downstream backend design skills.

Use the helper script:

```bash
python skills/design-backend-read-inputs/scripts/read_inputs.py \
  --final-prd artifacts/prd/final_prd.json \
  --repo-context repo_context.json \
  --service-inventory service_inventory.json \
  --architecture-constraints architecture_constraints.json \
  --existing-api-specs-dir existing_api_specs \
  --output artifacts/design/backend/repo_context_snapshot.json
```
