---
name: design.backend.quality_plan
description: >
  Generate backend quality and risk assets before coding starts.
  Use this skill whenever a user asks for idempotency, consistency, observability,
  rollout, rollback, or backend risk planning tied to the feature design.
---

Generate `quality_plan.json` and `risk_register.json`.

Inputs:
- `final_prd.json`
- `knowbase_context.json`

Outputs:
- `artifacts/design/backend/quality_plan.json`
- `artifacts/design/backend/risk_register.json`

Do this:
1. Define idempotency, consistency, concurrency, permission, observability, rollout, and rollback plans.
2. Convert unresolved gaps and non-functional pressure into explicit design risks.
3. Keep outputs aligned with [`quality_plan.schema.json`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/quality_plan.schema.json) and [`risk_register.schema.json`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/schemas/backend-design/risk_register.schema.json).

Use the helper script:

```bash
python skills/design-backend-quality-plan/scripts/generate_quality_plan.py \
  --final-prd artifacts/prd/final_prd.json \
  --knowbase-context artifacts/design/backend/knowbase_context.json \
  --quality-output artifacts/design/backend/quality_plan.json \
  --risk-output artifacts/design/backend/risk_register.json
```
