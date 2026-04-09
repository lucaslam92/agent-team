---
name: coding.compile_report
description: >
  汇总所有 Coding Mission 产物，生成人类可读的 coding_summary.md，供 Review / PR 阶段使用。
  在 coding.verify 通过后运行；凡是需要生成 coding 总结、编译 coding 报告，都应使用此 skill。
---

Inputs:
- `artifacts/coding/selected_task_batch.json`
- `artifacts/coding/changed_files.json`
- `artifacts/coding/coding_check_report.json`
- `artifacts/coding/verification_handoff.json`

Outputs:
- `artifacts/coding/coding_summary.md`

Do this:
1. Read generated coding artifacts from the artifacts directory.
2. Compile a human-readable summary grouped by endpoint and issues.
3. Write/update `coding_summary.md`.

Use the helper command:

```bash
python scripts/coding_compile_report.py --artifacts-dir artifacts/coding
```
