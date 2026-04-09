---
name: coding.verify
description: >
  运行 Coding Mission 的四个 gate，生成 coding_check_report.json 和
  verification_handoff.json。在 execute_tasks + run_verification_hooks 完成后
  必须运行此 skill；凡是用户说"检查 coding 结果"、"运行 coding gate"、
  "生成 coding check report"，都应触发此 skill。
---

# Coding Verify Skill

## 职责

对本轮 coding 产物（task batch、hook 结果、changed files、evidence）运行四个 gate，
输出结构化的 check report 和 verification handoff。

**不做**：不选任务、不执行 hook、不写代码。

## 四个 Gate

| Gate | 通过条件 |
|------|----------|
| `coding_input_ready_gate` | 无缺失输入字段 + design gate 已通过 |
| `coding_change_safety_gate` | 所有选中 task 均有 `design_artifact_refs`（无 drift） |
| `coding_verification_gate` | 无 failed hook + changed files 有对应 evidence |
| `coding_handoff_ready_gate` | 前三个 gate 通过 + schema 校验无 blocking 问题 |

## 输入

- `artifacts/coding/input_payload.json`
- `artifacts/coding/selected_task_batch.json`
- `artifacts/coding/hook_results.json`（可选，由 `coding.run_verification_hooks` 产出）
- `artifacts/coding/changed_files.json`（可选，由 `execute_tasks` 后填写）

## 输出

- `artifacts/coding/coding_check_report.json`
- `artifacts/coding/coding_design_trace.json`
- `artifacts/coding/verification_handoff.json`

## 执行

```bash
python scripts/verify_coding.py \
  --inputs artifacts/coding/input_payload.json \
  --selected-task-batch artifacts/coding/selected_task_batch.json \
  --hook-results artifacts/coding/hook_results.json \
  --changed-files artifacts/coding/changed_files.json \
  --output-dir artifacts/coding
```

加 `--execute-evidence` 可实际运行 compile/lint/integration/contract/smoke 命令。

## 结果解读

| `summary.status` | 含义 |
|-----------------|------|
| `passed` | 全部 gate 通过，可进入 Verification Mission |
| `degraded` | 有 medium 级别 warning，建议修复但不阻断 |
| `failed` | 有 high 级别 blocking issue，必须修复后重跑 |

## 失败处理

查看 `coding_check_report.json` 的 `open_issues` 和 `analyzer_results.repair_actions`：
- `coding-input-missing` → 补充缺失字段，重跑 `coding.read_inputs`
- `verification-hook-failed` → 修复 hook 失败原因，重跑 `coding.run_verification_hooks`
- `drift-design-ref-*` → 在对应 task 中补充 `design_artifact_refs`
- `schema-validation-failed-*` → 修复对应 artifact 的结构问题
