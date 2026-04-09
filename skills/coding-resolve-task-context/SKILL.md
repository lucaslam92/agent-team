---
name: coding.resolve_task_context
description: >
  为选定的 coding task batch 构建并持久化 execution_context.json，
  供 execute_tasks、run_verification_hooks、verify 等后续 skill 使用。
  在 select_task_batch 之后、execute_tasks 之前必须运行此 skill；
  凡是后续 skill 提示"找不到 execution_context"时也应触发。
---

# Coding Resolve Task Context Skill

## 职责

将 input_payload + selected_task_batch 整合为一份结构化的执行快照（execution_context.json），
记录本次 coding run 的所有引用来源，供下游 skill 直接消费，避免重复解析。

**不做**：不选任务、不执行 hook、不写代码。

## 输入

- `artifacts/coding/input_payload.json`
- `artifacts/coding/selected_task_batch.json`（由 `coding.select_task_batch` 产出）

## 输出

- `artifacts/coding/execution_context.json`

包含：

| 字段 | 说明 |
|------|------|
| `feature_id` | 本次运行的功能标识 |
| `platform` | backend / frontend / cross |
| `selected_checkpoint` | 本轮选定的 checkpoint |
| `task_graph_sources` | task graph 文件来源列表 |
| `design_asset_refs` | 所有 design asset 的 key 列表 |
| `repo_context_refs` | repo context 的字段 key 列表 |
| `endpoint_profiles` | 本 batch 涉及的 `endpoint::stack_profile` 组合 |

## 执行

```bash
python scripts/resolve_task_context.py \
  --inputs artifacts/coding/input_payload.json \
  --selected-task-batch artifacts/coding/selected_task_batch.json \
  --output artifacts/coding/execution_context.json
```

## 失败处理

| 问题 | 处理方式 |
|------|----------|
| `selected_task_batch.json` 不存在 | 先运行 `coding.select_task_batch` |
| `endpoint_profiles` 为空 | 检查 task 的 `endpoint` 和 `stack_profile` 字段是否填写 |
