---
name: coding.mission.mvp
description: >
  Run the Coding Mission MVP chain (read_inputs -> select_task_batch -> verify -> compile_report)
  and emit `selected_task_batch.json` plus `coding_check_report.json` for downstream verification.
  Use this when design artifacts are ready and you need constrained, traceable coding handoff outputs.
---

Execute Coding Mission MVP with a single command.

Inputs (single JSON file):
- `feature_id`
- `final_prd`
- `repo_context`
- `knowbase_context`
- `design_assets`
- `task_graph`
- `design_check_report`

Outputs (default under `artifacts/coding/`):
- `selected_task_batch.json`
- `coding_check_report.json`

Do this:
1. Ensure required input keys exist.
2. Confirm design gate status is `passed` or `degraded`.
3. Select ready tasks using dependency/blocking/design-asset checks.
4. Build the selected batch artifact and coding check report.

Use the helper script:

```bash
python scripts/run_coding_mission.py \
  --inputs artifacts/coding/input_payload.json \
  --output-dir artifacts/coding
```
