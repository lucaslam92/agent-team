---
name: coding.frontend.execute_tasks
description: >
  按 design artifact 约束实现 frontend task batch（page / component / state /
  data_binding / contract_adapter / interaction / accessibility / test），
  完成后填写 changed_files.json 并记录 hook 结果。
  凡是需要写前端代码、实现 frontend task、或完成 frontend coding 阶段，都应使用此 skill。
---

# Coding Frontend Execute Tasks Skill

## 职责

读取 `selected_task_batch.json` 中的 frontend 任务，按 design artifact 约束实现 UI 层，
记录实际修改的文件，输出 `frontend_task_execution.json`。

**关键原则**：不重新设计组件结构，不随意改 API 接口。严格消费 `contract_adapter` 和 `data_binding_plan`，
超出 scope 的改动必须停止并报告。

## 输入

- `artifacts/coding/selected_task_batch.json`（由 `coding.select_task_batch` 产出）
- `artifacts/coding/execution_context.json`（由 `coding.resolve_task_context` 产出）
- 各 task 的 `design_artifact_refs` 所指向的 design 文件（component_spec / state_model / data_binding_plan / interaction_spec / frontend_contract_view / quality_plan）

## 输出

- `artifacts/coding/frontend_task_execution.json`（hook 结果记录）
- `artifacts/coding/changed_files.json`（需要 Claude 在实现后手动填写或更新）

## 实现顺序

按以下 task_type 顺序执行，确保状态管理先于 UI 渲染：

```
state → page/component → contract_adapter/data_binding → interaction → accessibility/observability → test
```

## 每个 Task 的实现步骤

对每个 selected frontend task：

1. **读取 design artifact**：根据 `design_artifact_refs` 加载对应设计文件
2. **确认 scope**：对照 `done_when` 明确完成条件，确认哪些文件/组件在 scope 内
3. **实现代码**：按 design artifact 实现，不引入未定义的 state/prop/接口
4. **记录 changed_files**：把实际修改的文件路径追加到 `artifacts/coding/changed_files.json`
5. **执行 verification hooks**：完成实现后执行对应 hook
6. **记录结果**：把 hook 结果写到输出 JSON

## 按 task_type 的实现要点

| task_type | 参考 artifact | 关键约束 |
|-----------|---------------|----------|
| `state` | `state_model.json` | state shape / action / selector 严格按 model |
| `page` | `page_map.json` + `ui_structure.json` | 路由路径/页面布局按 page_map |
| `component` | `component_spec.json` | props interface、slots、emit 按 spec 定义 |
| `contract_adapter` | `frontend_contract_view.json` | request/response 映射完全来自 contract view |
| `data_binding` | `data_binding_plan.json` | loading/error/empty state 按 plan 处理 |
| `interaction` | `interaction_spec.json` | 动画/手势/键盘行为按 spec，不自创 |
| `accessibility` | `quality_plan.json` | ARIA / 对比度 / 键盘导航按 quality 要求 |
| `test` | `quality_plan.json` | 覆盖 done_when 中的 acceptance 条件 |

## 执行辅助命令

```bash
python scripts/coding_frontend_execute_tasks.py \
  --selected-task-batch artifacts/coding/selected_task_batch.json \
  --output artifacts/coding/frontend_task_execution.json \
  --execute-hooks
```

> 加 `--execute-hooks` 在实现后自动执行 verification hooks。

## 失败处理

| 问题 | 处理方式 |
|------|----------|
| 实现超出 design scope | 停止，记录 blocked，等待 design 更新 |
| `frontend_contract_view` 与 backend API 实际不一致 | 报告 contract drift，不自行调整 |
| hook 执行失败 | 记录原因，交给 `coding.verify` 评估 |
