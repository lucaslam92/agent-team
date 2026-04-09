---
name: coding.resolve_task_context
description: >
  Build execution_context for the selected coding task batch before implementation and verification.
---

Inputs:
- `artifacts/coding/input_payload.json`
- `artifacts/coding/selected_task_batch.json`

Outputs:
- `artifacts/coding/execution_context.json`

Do this:
1. Read mission input snapshot and selected checkpoint.
2. Resolve task graph/design/repo context references.
3. Persist execution_context for downstream coding/verification artifacts.

Use the helper command:

```bash
python scripts/run_coding_mission.py \
  --inputs artifacts/coding/input_payload.json \
  --output-dir artifacts/coding
```
