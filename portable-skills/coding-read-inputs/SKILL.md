---
name: coding.read_inputs
description: >
  Read and validate Coding Mission input contract.
---

Inputs:
- `artifacts/coding/input_payload.json`

Outputs:
- `artifacts/coding/selected_task_batch.json`
- `artifacts/coding/coding_check_report.json`

Do this:
1. Read/validate mission inputs from the payload.
2. Respect design gate and dependency constraints.
3. Produce structured artifacts for verification handoff.

Use the helper command:

```bash
python scripts/run_coding_mission.py --inputs artifacts/coding/input_payload.json --output-dir artifacts/coding
```
