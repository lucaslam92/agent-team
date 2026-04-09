---
name: coding.run_verification_hooks
description: >
  Execute or plan verification hooks for selected coding tasks and emit structured hook results.
---

Inputs:
- `artifacts/coding/selected_task_batch.json`

Outputs:
- `artifacts/coding/hook_results.json`

Do this:
1. Read selected tasks and their `verification_hooks`.
2. Execute hooks when requested, otherwise emit planned status.
3. Persist structured hook execution results for coding.verify and handoff.

Use the helper command:

```bash
python scripts/run_verification_hooks.py \
  --selected-task-batch artifacts/coding/selected_task_batch.json \
  --output artifacts/coding/hook_results.json \
  --execute
```
