# Knowledge Topology

## Goal

知识体系采用“中央知识库仓库 + repo-local overlay”双层模型，目的是同时满足：

- 跨仓库共享长期知识
- 每个代码仓库保留自己的实现特例
- 知识沉淀可以持续自动化

## Global Knowledge Repository

中央知识库仓库负责存放共享知识真相：

- `knowledge/`
  - 业务背景
  - 通用架构原则
  - 平台规则
  - ADR
  - playbooks
- `semantic-store/`
  - 跨仓库共享的正式结构化知识
  - 共享 graph index

这层适合团队统一维护，变更频率低于业务代码仓库。

## Repo-Local Overlay

各端代码仓库需要保留本地覆盖层：

- `artifacts/`
  - 当前任务输入输出
- `knowledge/rules/local/`
  - 本仓特有规则
- `knowledge/capabilities/local/`
  - 本仓可用能力补充
- `knowledge/playbooks/local/`
  - 本仓运行手册
- `semantic-store/generated/`
  - 自动收集的候选知识
- `semantic-store/state/`
  - 增量扫描、晋升、去重状态

本地 overlay 可以依赖中央知识库，但不能静默覆盖中央规则；覆盖必须明确、可追踪。

## Resolution Priority

Resolver 和 Mission 的默认优先级固定为：

1. repo-local normalized knowledge
2. repo-local local rules / capabilities / playbooks
3. platform/shared normalized knowledge
4. global normalized knowledge
5. long-form `knowledge/` documents as fallback context

## Synchronization Strategy

推荐同步策略：

- 代码仓库内持续运行 collector/promoter，形成本地候选和正式知识
- 对高置信度、跨仓库可复用的正式知识，定期回流到中央知识库仓库
- 中央知识库仓库发布后，再被各代码仓库拉取或镜像使用

## What Stays Local

以下内容通常应保留在代码仓库内：

- 当前 repo 的模块边界和实现细节
- 当前 repo 的组件限制与反模式
- 与当前 repo 强绑定的容量瓶颈
- 当前任务产生的 artifacts

## What Moves Global

以下内容更适合沉淀到中央知识库仓库：

- 业务术语和核心领域模型
- 跨端一致的规则
- 公共能力与平台边界
- 共享容量基线与通用性能预算
- 可复用 playbook
