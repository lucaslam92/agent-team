---
name: coding.select_task_batch
description: >
  从 task_graph 中选出本轮可执行的 ready task batch，写出 selected_task_batch.json。
  当需要确定本轮应该实现哪些任务、或 Coding Mission 刚通过输入校验准备进入实现阶段时，
  必须使用此 skill；即使用户说"选择本次 coding 任务"也应触发。
---

# Coding Select Task Batch Skill

## 职责

从 `task_graph` 中筛选 ready tasks，确定本轮实现批次，写出 `selected_task_batch.json`。

**不做**：不执行 hook、不写代码、不做任何实现。

## Ready Task 判定条件（全部满足才入选）

| 条件 | 说明 |
|------|------|
| `depends_on` 已满足 | 所有依赖任务的 status = done |
| 未被 `blocked` | `task.blocked` 不为 true |
| `design_assets_ready` | 字段为 true 或未声明 |
| `checkpoint` 匹配 | 与 task_graph 声明的当前 checkpoint 一致 |
| `design_artifact_refs` 非空 | 任务必须链接到至少一个设计资产 |

> `changed_files` **不是** ready 条件——它是执行后的输出产物，不要求预先声明。

## Batch 优先级

按以下顺序优先选入：
1. `blocking=true` 的任务
2. 当前 checkpoint 内的任务
3. `priority=high` 的任务

## 输入

- `artifacts/coding/input_payload.json`

## 输出

- `artifacts/coding/selected_task_batch.json`

包含：`selected_tasks`、`skipped_tasks`、`selection_reasons`、`unresolved_dependencies`、`execution_order`。

## 执行

```bash
python scripts/select_task_batch.py \
  --inputs artifacts/coding/input_payload.json \
  --output artifacts/coding/selected_task_batch.json \
  --max-tasks 10
```

## 失败处理

| 问题 | 处理方式 |
|------|----------|
| 没有任何 ready task | 检查 `skipped_tasks.reason`，补充依赖或修正 checkpoint |
| `unresolved_dependencies` 非空 | 先完成依赖任务再重跑 |
| design gate 未通过 | 先运行 `coding.read_inputs` 诊断 |
