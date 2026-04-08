# System Overview

## Layers

系统按四层组织：

- Mission Artifacts：当前任务阶段的输入输出真相
- Agent Instructions：仓库级或目录级执行规则
- Skills：可复用的工作流能力
- Knowledge + Semantic Store：长期知识与结构化语义层

## Structural Split

推荐固定为两层知识结构：

- `knowledge/`
  - 长期人类可读知识
  - 例如业务背景、架构说明、规则、ADR、playbooks
- `semantic-store/`
  - 结构化语义知识
  - 包含 `generated/`、`normalized/`、`index/`、`state/`

## Global And Local Overlay

知识体系推荐按“中央知识库仓库 + repo-local overlay”运行：

- 中央知识库仓库
  - 放共享业务背景、平台规则、ADR、容量基线
  - 放跨仓库可复用的 `semantic-store/normalized/` 与 `index/`
- 各端代码仓库
  - 放 repo-local `artifacts/`
  - 放 repo-local `knowledge/rules/local/`、`knowledge/capabilities/local/`
  - 放 repo-local `semantic-store/generated/`、`state/`

运行时优先级固定为：

`repo-local > platform/shared > global`

## Mission Flow

默认研发闭环为：

`PRD -> Design -> Coding -> Verification -> PR`

每一阶段都应把当前输出写入 `artifacts/`，作为后续阶段的输入真相。

## Retrieval And Semantics

- Graph layer 负责从多源 signals 构建 `nodes.json` / `edges.json`
- Semantic layer 负责把 graph 证据提升为 Feature / Rule / Capability 等卡片
- Mission 层默认消费正式语义知识，而不是直接消费原始候选

## Source Of Truth

- 当前任务真相：`artifacts/`
- 长期文档知识：`knowledge/`
- 正式结构化知识：`semantic-store/normalized/`
- 结构化候选与状态：`semantic-store/generated/`、`semantic-store/state/`

## Platform Knowledge Themes

当前长期知识建议至少覆盖：

- 前端技术栈、组件使用约束、状态管理与导航边界
- 后端模块划分、分层、同步/异步边界、可靠性要求
- API 契约与兼容性规则
- 容量与性能预算、SLO、扩缩容约束

## Working Rule

- 变更当前任务时，优先更新 `artifacts/`
- 沉淀长期说明时，更新 `knowledge/`
- 沉淀结构化卡片时，更新 `semantic-store/`
