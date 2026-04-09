---
name: coding.mission.mvp
description: >
  一键运行完整 Coding Mission MVP 链路（read_inputs → select_task_batch → verify → compile_report），
  产出 selected_task_batch.json 和 coding_check_report.json。
  当 design artifacts 已就绪、需要一次性完成 coding 准备和 gate 检查时使用此 skill；
  即使用户只说"运行 coding mission"也应优先触发此 skill，而不是逐个调用子 skill。
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
