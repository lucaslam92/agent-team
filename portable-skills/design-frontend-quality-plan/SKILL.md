---
name: design.frontend.quality_plan
description: >
  Generate frontend quality and risk assets before coding starts.
  Use this skill whenever a user asks for accessibility, performance budgets,
  UI error handling, rollout plans, fallback plans, or frontend design risks.
---

Generate `quality_plan.json` and `risk_register.json`.

Use the script:

```bash
python skills/design-frontend-quality-plan/scripts/generate_quality_plan.py \
  --final-prd artifacts/prd/final_prd.json \
  --knowbase-context artifacts/design/frontend/knowbase_context.json \
  --quality-output artifacts/design/frontend/quality_plan.json \
  --risk-output artifacts/design/frontend/risk_register.json
```
