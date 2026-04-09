---
name: coding.compile_report
description: >
  Compile Coding Mission artifacts for verification handoff.
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
