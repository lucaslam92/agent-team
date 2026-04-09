---
name: coding.backend.execute_tasks
description: >
  按 design artifact 约束实现 backend task batch（domain / storage / api / event / job / test），
  完成后填写 changed_files.json，并调用脚本记录 hook 结果。
  凡是需要写后端代码、实现 backend task、或完成 backend coding 阶段，都应使用此 skill。
---

# Coding Backend Execute Tasks Skill

## 职责

读取 `selected_task_batch.json` 中的 backend 任务，按 design artifact 约束写代码，
记录实际修改的文件，输出 `backend_task_execution.json`。

**关键原则**：不重新设计、不重新拆任务。完全按 design artifact 实现，超出 scope 的改动必须停止并报告。

## 输入

- `artifacts/coding/selected_task_batch.json`（由 `coding.select_task_batch` 产出）
- `artifacts/coding/execution_context.json`（由 `coding.resolve_task_context` 产出）
- 各 task 的 `design_artifact_refs` 所指向的 design 文件（domain_model / api_contract / flow_model / storage_plan / quality_plan）

## 输出

- `artifacts/coding/backend_task_execution.json`（hook 结果记录）
- `artifacts/coding/changed_files.json`（需要 Claude 在实现后手动填写或更新）

## 实现顺序

按以下 task_type 顺序执行，确保依赖正确：

```
domain → storage → api → event/job → observability → test
```

## 每个 Task 的实现步骤

对每个 selected backend task：

1. **读取 design artifact**：根据 `design_artifact_refs` 加载对应设计文件（domain_model / api_contract 等）
2. **确认 scope**：对照 `done_when` 明确本 task 的完成条件，确认哪些文件在 scope 内
3. **实现代码**：按 design artifact 写代码，不引入未在 design 中定义的接口/字段
4. **记录 changed_files**：把实际修改的文件路径追加到 `artifacts/coding/changed_files.json`
5. **执行 verification hooks**：完成实现后立即执行对应 hook（`task.verification_hooks`）
6. **记录结果**：把 hook 结果写到输出 JSON

## 按 task_type 的实现要点

| task_type | 参考 artifact | 关键约束 |
|-----------|---------------|----------|
| `domain` | `domain_model.json` | 实体字段/关系/值对象严格按 model，不随意增删 |
| `storage` | `storage_plan.json` | migration 需幂等，schema 变更必须向前兼容 |
| `api` | `api_contract.yaml` | 路由/请求体/响应结构按 contract，不静默破坏现有 endpoint |
| `event` | `flow_model.json` | 事件命名、payload 结构、幂等处理按 flow model |
| `job` | `flow_model.json` | 重试策略、失败处理按 quality_plan |
| `test` | `quality_plan.json` | 覆盖 done_when 中的 acceptance 条件 |

## 执行辅助命令

```bash
python scripts/coding_backend_execute_tasks.py \
  --selected-task-batch artifacts/coding/selected_task_batch.json \
  --output artifacts/coding/backend_task_execution.json \
  --execute-hooks
```

> 加 `--execute-hooks` 在实现完成后自动执行 verification hooks。
> 不加时只记录 planned 状态，需要手动运行 `coding.run_verification_hooks`。

## 失败处理

| 问题 | 处理方式 |
|------|----------|
| 实现超出 design scope | 停止实现，在 task 的 notes 中记录，等待架构确认 |
| design artifact 有歧义或缺失 | 停止，报告 blocked，不猜测实现意图 |
| hook 执行失败 | 记录失败原因，不要忽略，交给 `coding.verify` 评估 |
