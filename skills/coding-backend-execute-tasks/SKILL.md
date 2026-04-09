---
name: coding.backend.execute_tasks
description: >
  Execute backend task batch in constrained order and collect change evidence.
---

Inputs:
- `artifacts/coding/selected_task_batch.json`

Outputs:
- `artifacts/coding/backend_task_execution.json`

Do this:
1. Load selected task batch and filter backend endpoint tasks.
2. Execute or plan verification hooks per task.
3. Output backend execution evidence as JSON.

Use the helper command:

```bash
python scripts/coding_backend_execute_tasks.py --selected-task-batch artifacts/coding/selected_task_batch.json --output artifacts/coding/backend_task_execution.json
```
