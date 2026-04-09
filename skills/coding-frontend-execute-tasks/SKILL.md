---
name: coding.frontend.execute_tasks
description: >
  Execute frontend task batch in constrained order and collect change evidence.
---

Inputs:
- `artifacts/coding/selected_task_batch.json`

Outputs:
- `artifacts/coding/frontend_task_execution.json`

Do this:
1. Load selected task batch and filter frontend endpoint tasks.
2. Execute or plan verification hooks per task.
3. Output frontend execution evidence as JSON.

Use the helper command:

```bash
python scripts/coding_frontend_execute_tasks.py --selected-task-batch artifacts/coding/selected_task_batch.json --output artifacts/coding/frontend_task_execution.json
```
