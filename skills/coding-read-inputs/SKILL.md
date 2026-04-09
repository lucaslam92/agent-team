---
name: coding.read_inputs
description: >
  Coding Mission 的入口校验关卡。验证 input_payload.json 包含全部必要字段
  并确认 design gate 已通过（status=passed 或 degraded）。
  凡是不确定 Coding Mission 输入是否就绪、或需要诊断输入缺失问题时，
  必须先用此 skill；即使用户只说"检查 coding 输入"也应触发。
---

# Coding Read Inputs Skill

## 职责

验证 Coding Mission 的入口合同是否满足，防止因输入不完整导致后续阶段静默失败。

**不做**：不选任务、不写任何 coding artifact、不执行 hook。

## 输入

- `artifacts/coding/input_payload.json`

必须包含以下字段：

| 字段 | 说明 |
|------|------|
| `final_prd` | 来自 PRD Mission 的需求合同 |
| `repo_context` | 仓库结构、模块边界、技术栈 |
| `knowbase_context` | 已收敛的 rules / constraints / anti-patterns |
| `design_assets` | Backend/Frontend Design Mission 的设计产物（路径 map） |
| `task_graph` | 包含 `tasks[]`、`checkpoint`、`platform` 的任务图 |
| `design_check_report` | Design gate 报告，`summary.status` 必须为 `passed` 或 `degraded` |

## 执行

```bash
python scripts/select_task_batch.py \
  --inputs artifacts/coding/input_payload.json \
  --output /dev/null \
  --max-tasks 0
```

> `--max-tasks 0` 表示只做输入校验，不写出任何 artifact。
> 失败时脚本返回非零退出码，并打印缺失字段或 gate 原因。

## 失败处理

| 问题 | 处理方式 |
|------|----------|
| 缺少必要输入字段 | 列出所有缺失字段，要求补充后重跑 |
| `design_check_report` 未通过 | 先运行 Design Verify 修复 gate，再重新进入 Coding Mission |
