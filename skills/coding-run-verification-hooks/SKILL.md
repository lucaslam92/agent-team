---
name: coding.run_verification_hooks
description: >
  执行 selected task batch 中每个任务声明的 verification_hooks，写出 hook_results.json。
  在 execute_tasks 完成后、coding.verify 之前必须运行；凡是需要执行 coding verification hooks、
  或检查 hook 执行结果，都应使用此 skill。
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
