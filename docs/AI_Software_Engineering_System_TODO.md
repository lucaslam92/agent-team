# AI Software Engineering System TODO

本文档用于维护当前系统从 PRD Mission 向完整 AI Software Engineering System 演进时的待补功能、优先级和实施顺序。

设计原则、架构目标和长期方向保留在：

[`docs/PRD_Mission_Design_v3.md`](./PRD_Mission_Design_v3.md)

---

## 1. 当前缺口总览

当前仓库已经具备 PRD Mission 主链路与部分 resolver / validation 脚本，但系统级目标与现状之间仍存在以下关键缺口：

新增约束：

- 新方案必须可供 Claude Code / Claude CLI 使用
- 新能力必须优先以标准 Claude skill 方式实现
- 不应把核心运行链路绑定到 Codex 私有配置

### P0：Graph 主链路未落地

- 缺少 `build_graph.py`
- 缺少 `graph_retrieve.py`
- `context-build` 仍以 `retrieve_knowledge.py` 为主入口
- 当前检索仍以 keyword / domain 打分为主，不是 graph retrieval
- Graph 相关能力还未以标准 Claude skill 形式封装

### P1：语义提升与 graph-aware 解析未落地

- 缺少 `code-to-knowledge-interpreter`
- `resolve_rules.py` 尚未消费 `subgraph.json`
- `resolve_capabilities.py` 尚未消费 `subgraph.json`
- resolver 还未引入 graph proximity 排序
- 这些能力还未拆分为可供 Claude Code / Claude CLI 直接调用的 skill

### P1：架构治理文件缺失

- 缺少 `docs/architecture_state.json`
- 缺少 `docs/adr/`
- 缺少 ADR-001 / ADR-002 / ADR-003 初稿

### P2：现有 PRD 流程遗留能力未补齐

- `resolve_resources.py` 的 MCP fetch 仍为 STUB
- 外部资源获取仍会落到 `pending_mcp`
- 旧的 keyword 路线仍在上下文链路中保留

---

## 2. 推荐实施顺序

建议按以下顺序推进：

1. 定义标准 Claude skill 拆分方案
2. 落地 `build_graph.py`
3. 落地 `graph_retrieve.py`
4. 改造 `context-build`，移除 `retrieve_knowledge`
5. 新增 `code-to-knowledge-interpreter`
6. 改造 `resolve_rules.py` / `resolve_capabilities.py`
7. 补齐 `docs/architecture_state.json`
8. 补齐 `docs/adr/ADR-001.md` ~ `ADR-003.md`
9. 补齐 `resolve_resources.py` 的 MCP 接入

这样可以先建立 Graph Layer，再逐步替换旧的检索和解析链路，避免系统长期停留在 keyword 与 graph 双轨并行状态。

---

## 3. Backlog

## 3.0 P0：定义标准 Claude skill 实现方式

### TODO-000 标准化 skill 交付方式

目标：

- 确保新方案可以被 Claude Code 与 Claude CLI 直接使用
- 所有新增核心能力优先按标准 Claude skill 目录组织

最低要求：

- 每个新增能力对应独立 skill 目录
- skill 根目录包含 `SKILL.md`
- 仅在需要时增加 `scripts/`、`references/`、`assets/`
- `SKILL.md` 的 frontmatter `description` 需要写清楚触发场景

建议拆分：

- `graph-builder`
- `graph-retrieve`
- `code-to-knowledge-interpreter`
- `graph-aware-resolver`
- `architecture-sync`

完成标准：

- 能明确这些能力分别由哪个 skill 承担
- skill 间输入输出契约清楚
- 不依赖 Codex 私有 UI 配置作为运行前提

## 3.1 P0：建立 Graph Layer

### TODO-001 `build_graph.py`

目标：

- 从多源 `signals` 构建统一 `nodes.json` / `edges.json`
- 支持增量构建
- 输出 `graph_meta.json`

建议输出：

- `semantic-store/index/nodes.json`
- `semantic-store/index/edges.json`
- `semantic-store/index/graph_meta.json`

完成标准：

- 能从输入 signals 生成稳定 node id
- 能生成 `calls` / `depends_on` / `related_to` / `implements` 等边
- 能校验非法 relation 和基础图完整性
- 能作为独立 Claude skill 的脚本资源被调用

### TODO-002 `graph_retrieve.py`

目标：

- 从 query 定位 seed nodes
- 支持 k-hop expansion
- 输出供 interpreter 使用的 `subgraph.json`

完成标准：

- 支持 `--hops`
- 支持 `--max-nodes`
- 输出 `seed_nodes`、`expanded_nodes`、`expanded_edges`、`scores`
- 能作为独立 Claude skill 的脚本资源被调用

### TODO-003 改造 `context-build`

目标：

- 移除 `retrieve_knowledge.py` 作为主入口
- 将 Stage 2 改为 graph retrieval 主链路

目标链路：

```text
intake_result
-> graph_retrieve
-> subgraph
-> interpreter
-> cards
-> resolve_rules
-> resolve_capabilities
-> context_summary
```

完成标准：

- `skills/context-build/SKILL.md` 更新为 graph 路线
- 输出物和下游接口保持兼容
- 新链路可由 Claude Code / Claude CLI 通过标准 skill 调用

---

## 3.2 P1：建立 Semantic 提升链路

### TODO-004 `code-to-knowledge-interpreter`

目标：

- 将 subgraph 转换为 Feature / Rule / Capability Card
- 合并多端信号
- 建立依赖关系

输入：

```json
{
  "signals": {},
  "existing_knowbase": {}
}
```

输出：

```json
{
  "feature_cards": [],
  "rule_cards": [],
  "capability_cards": []
}
```

完成标准：

- 输出结构稳定
- 不承担 persist / dedupe / index
- 与后续 normalize / dedupe 流程衔接清晰
- 以独立 skill 形式存在，便于 Claude Code / Claude CLI 复用

### TODO-005 graph-aware `resolve_rules.py`

目标：

- 在现有 scope / stage / override 逻辑上接入 graph 信号
- 支持消费 `subgraph.json`

完成标准：

- 排序不再只基于 keyword / domain
- graph proximity 纳入评分
- 保持 `override_trace` 输出不回退

### TODO-006 graph-aware `resolve_capabilities.py`

目标：

- 能消费 `subgraph.json`
- 将 graph proximity 纳入排序

建议排序：

```text
graph_score * 0.5 + domain_score * 0.3 + availability_score * 0.2
```

完成标准：

- 仍保持 ready 优先
- 输出结构与现有下游兼容

---

## 3.3 P1：补齐架构治理

### TODO-007 `docs/architecture_state.json`

目标：

- 固化系统当前启用的 layer、retrieval、resolver、policy

最低要求：

- graph 是否启用
- retrieval 类型
- resolver 优先级
- keyword retrieval 禁止策略

### TODO-008 ADR 初稿

需要新增：

- `docs/adr/ADR-001-graph-layer.md`
- `docs/adr/ADR-002-knowbase-schema.md`
- `docs/adr/ADR-003-interpreter.md`

目标：

- 固化关键架构决策
- 约束后续 skill / mission / script 演进方向
- 明确哪些能力必须以标准 Claude skill 方式实现

---

## 3.4 P2：补齐现有流程遗留项

### TODO-009 MCP 接入 `resolve_resources.py`

当前状态：

- `fetch_via_mcp()` 仍为 `NotImplemented`
- 外部资源只能标记为 `pending_mcp`

目标：

- 接入 GDoc / GSheet / Figma / Confluence fetch
- 将资源正文与元数据落盘到 artifact 目录

完成标准：

- `resource_index.json` 中可产出 `resolved`
- 失败时仍保留 `fetch_failed`，不阻塞主流程

### TODO-010 清理旧 keyword 路线

目标：

- 在 graph 路线稳定后，清理 `retrieve_knowledge.py` 的主链路职责
- 将旧逻辑降级为 fallback 或彻底移除

---

## 4. 当前建议

如果只做一件最值回票价的事，应优先实现：

- 标准 Claude skill 拆分方案
- `build_graph.py`
- `graph_retrieve.py`
- `context-build` 的 graph 化改造

这是系统从“能跑 PRD 流程”升级到“可被 Claude Code / Claude CLI 复用的知识驱动软件工程系统”的关键分水岭。
