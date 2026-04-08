# Knowbase 积累设计文档（v1）

## 1. 目标

本文档定义 AI Software Engineering System 中 Knowbase 的持续积累方案。

目标不是构建两套独立知识库，而是构建一条统一的知识沉淀流水线，使系统能够同时支持：

- 需求迭代闭环后的正式知识沉淀
- 从 code / PRD / 其他工程文档的持续自动收集

统一目标链路为：

```text
signals
-> graph
-> interpreter
-> candidate cards
-> dedupe
-> promote
-> normalized knowbase
```

## 2. 设计原则

### 2.1 单一知识真相

系统只维护一份可消费的正式 Knowbase。自动收集和任务沉淀都不应直接绕过治理规则写入正式层。

### 2.2 generated 与 normalized 分层

- `generated/` 保存机器生成的候选知识
- `normalized/` 保存可被 Mission 和 Resolver 直接消费的正式知识

这一区分是必要的，因为自动采集天然会带来噪声、重复和时效性问题。

### 2.3 Graph 优先

所有知识积累均应优先基于 graph 和 evidence，而不是直接基于 keyword 命中做归纳。

### 2.4 语义与确定性分离

- Graph 构建、去重、落盘、索引重建由脚本完成
- Feature / Rule / Capability 的语义提升由 interpreter 完成

### 2.5 Mission 只默认消费正式知识

Mission 默认只读取 `semantic-store/normalized/`。如需参考 `semantic-store/generated/`，必须显式进入探索模式或候选增强模式。

## 3. 统一分层模型

建议采用“`knowledge/` + `semantic-store/`”双层结构：

```text
knowledge/
  business/
  architecture/
  rules/
  decisions/
  playbooks/
semantic-store/
  generated/
    inbox/
    candidates/
    merge-reports/
  normalized/
    features/
    rules/
      business/
      platform/
      engineering/
    capabilities/
    playbooks/
    capacity/
  index/
    nodes.json
    edges.json
    graph_meta.json
  state/
    source_registry.json
    promotion_state.json
    dedupe_index.json
```

各层职责如下：

- `knowledge/`: 长期人类可读知识，如业务背景、架构、规则、ADR、playbook
- `semantic-store/generated/inbox/`: 原始候选卡片与中间产物
- `semantic-store/generated/candidates/`: 已标准化但未晋升的候选知识
- `semantic-store/generated/merge-reports/`: 去重、冲突、晋升决策报告
- `semantic-store/normalized/`: 正式知识
- `semantic-store/index/`: graph retrieval 使用的索引
- `semantic-store/state/`: 增量扫描、晋升状态、去重映射等系统状态

## 4. 两条积累路径

### 4.1 路径 A：需求迭代闭环后的正式沉淀

这是高质量主路径。

典型触发条件：

- PRD 定稿
- 设计评审通过
- 代码合并
- 验证通过
- PR 合并

推荐链路：

```text
mission outputs
+ merged code
+ verification artifacts
-> extract signals
-> build_graph
-> interpreter
-> candidate cards
-> dedupe
-> promote
-> normalized knowbase
```

该路径适合直接沉淀：

- Feature Card
- Rule Card
- Capability Card
- Playbook Card
- Capacity Profile Card

特点：

- 上下文完整
- 证据链更强
- 适合作为正式知识主来源

### 4.2 路径 B：自动收集与候选沉淀

这是规模化补充路径。

典型输入源：

- repo 中新增或变更的代码
- PRD / Design / API / ADR 文档
- README / Runbook / 运维文档
- PR 描述、评审记录、验证报告

推荐链路：

```text
repo/docs changes
-> extract signals
-> build_graph
-> interpreter
-> candidate cards
-> generated/
```

该路径默认只进入候选层，不直接进入 `normalized/`。

特点：

- 覆盖面大
- 增量性强
- 质量波动更大
- 需要显式晋升治理

### 4.2.1 当前已实现的 source adapters

当前仓库中的 `knowledge-collector` 已经具备首版脚本实现，核心入口为：

```text
skills/knowledge-collector/scripts/collect_knowledge.py
```

当前已支持的输入源包括：

- `PRD / Design / README / 通用文档`
  - 按标题和 section 拆分
  - 抽取 rule-like sentences
  - 抽取 capability-like lines
- `Architecture / Rules / Capacity Docs`
  - 抽取 architecture lines
  - 抽取 tech stack lines
  - 抽取 frontend component constraints
  - 抽取 capacity and performance constraints
- `Code`
  - 抽取 imports
  - 抽取 class / function / symbol
  - 对 service-like symbol 建能力信号
- `API 文档`
  - 抽取 endpoint
  - 抽取 `HTTP verb + path`
- `Mission Artifacts`
  - 支持 `context_summary`
  - 支持 `effective_rules`
  - 支持 `effective_capabilities`
  - 支持 `final_prd`
  - 支持 `mission_result`、`review_result`、`validation_result`
- `PR metadata`
  - 支持 PR title / body / labels / changed files
- `Git changeset`
  - 支持基于 `git diff` 或 merge 范围生成 changeset signal

这些 adapter 的职责是把不同输入源先统一转换成 graph-friendly signals，再进入：

```text
signals
-> build_graph
-> graph_retrieve
-> interpreter
-> candidate cards
```

### 4.2.2 当前实现边界

虽然上述输入源已经有脚本支持，但当前仍属于“首版可用”而不是“最终完备版”，主要边界包括：

- 文档解析仍以 section / sentence / line 级启发式为主，不是领域专用 parser
- code 抽取仍以通用符号和 import 关系为主，还没有深度语言语义分析
- API 抽取目前主要依赖 endpoint / path pattern，而不是完整 OpenAPI 语义解释
- mission artifacts 主要覆盖通用字段和常见列表字段，尚未对每个 mission 产物做强 schema 适配
- PR metadata 已可参与候选沉淀，但“PR merge 自动触发”目前仍以手动命令方式实现

因此，当前结论应理解为：

- “自动从 code / PRD / 其他文档收集 knowbase 候选”已经有实现
- 但后续仍可继续增强 adapter 深度和不同源的专用抽取质量

### 4.3 仓库级执行入口

为避免 `knowledge-collector`、`knowledge-promoter`、索引刷新三步在日常使用中分散执行，仓库提供统一入口：

```text
scripts/run_knowbase_accumulation.py
```

推荐执行链路：

```text
sources
-> knowledge-collector
-> generated/candidates
-> knowledge-promoter
-> normalized/
-> rebuild_semantic_index
-> index/
```

适用场景：

- 一个 mission 完成后沉淀本轮 artifacts 与代码变化
- PR 合并后吸收代码、文档、PR metadata
- 定期增量扫描，维护 `semantic-store/` 持续新鲜

对于“PR 已经 merge，需要人工正式晋升”的场景，仓库提供单独入口：

```text
scripts/run_pr_merge_promotion.py
```

该入口语义上等同于“手动触发一次 PR merge 正式晋升”：

- 默认读取当前 `HEAD`
- 若 `HEAD` 是 merge commit，则使用 `HEAD^1..HEAD`
- 若 `HEAD` 不是 merge commit，则回退到 `HEAD~1..HEAD`
- 然后执行 `collector -> promoter -> index refresh`

这使得团队即使暂时不接 Git 平台 webhook，也能在 PR merge 后手动触发一次正式知识沉淀。

为降低日常使用成本，仓库还提供了一个更短的命令入口：

```bash
make knowbase-pr-merge
```

## 5. 统一对象模型

所有 card 建议增加统一治理字段：

```json
{
  "id": "capability_order_submit_v2",
  "status": "candidate | approved | deprecated",
  "confidence": 0.86,
  "source_refs": [],
  "evidence": [],
  "derived_from": [],
  "last_verified_at": "2026-04-07T00:00:00Z",
  "promotion_policy": "manual_review | auto_promote"
}
```

字段含义：

- `status`: 当前生命周期状态
- `confidence`: 当前候选或正式知识的置信度
- `source_refs`: 对应源文件、任务、PR、文档等引用
- `evidence`: 支撑该知识的图节点、边、代码片段、文档段落
- `derived_from`: 来源链路，例如 mission、collector、manual-merge
- `last_verified_at`: 最近一次被代码或任务闭环验证的时间
- `promotion_policy`: 是否允许自动晋升

## 6. 卡片类型与晋升策略

### 6.1 Feature Card

建议要求：

- 至少存在 PRD / Design 类证据
- 最好再存在代码实现或 PR 合并证据

策略：

- 有需求证据但无实现时，允许进入 `candidate`
- 有实现和验证证据后，优先晋升为 `approved`

### 6.2 Rule Card

建议要求：

- 配置、校验逻辑、接口契约、测试用例等证据优先
- 纯文档推断默认不直接晋升

策略：

- 文档-only 规则先进入 `candidate`
- 多源证据一致后再晋升

### 6.3 Capability Card

这是最适合自动沉淀的一类。

建议要求：

- 代码中存在明确接口、模块、服务或可复用能力
- graph 中有 `implements`、`calls`、`depends_on` 等支撑关系

策略：

- 高置信度时允许自动晋升
- 必须保留 `availability`、`scope`、`interfaces`

### 6.4 Playbook Card

该类知识更偏执行经验，建议默认人工审核后晋升。

### 6.5 Capacity Profile Card

该类知识时效性强，建议默认人工审核，且必须带时间戳和证据来源。

## 7. 去重与冲突治理

不建议只基于文本相似度去重，应组合三层判断：

### 7.1 标识级去重

依据：

- 稳定 card id
- repo + path + symbol
- API name
- service / module 唯一标识

### 7.2 图结构级去重

依据：

- dependency 邻域
- 调用链
- 所属 domain
- 上下游模块

### 7.3 语义级去重

依据：

- 语义等价
- 能力重命名
- 版本替代

冲突关系建议标准化为：

- `same_as`
- `supersedes`
- `conflicts_with`

冲突不应直接覆盖原卡片，而应输出 merge report，再由 promoter 决定：

- 合并
- 保留多版本
- 标记废弃
- 升级为 superseded

## 8. 核心组件设计

### 8.1 Knowledge Collector

定位：

- 自动收集和生成候选知识的入口 skill

职责：

- 扫描 code / docs / mission artifacts
- 判断哪些输入需要增量抽取
- 驱动 extract -> graph -> interpreter
- 输出候选卡片到 `generated/`
- 维护 `state/source_registry.json`

首版 source adapters 建议至少覆盖：

- PRD / Design：按标题与规则句拆出 feature / rule / capability 信号
- ADR：按 Context / Decision / Consequence 拆出 rule 与 concept 信号
- Code：按文件、符号、依赖导出 code / service / depends_on 信号
- API：按 endpoint 导出 api 节点和实现关系
- Mission Artifacts：按 `context_summary`、`effective_rules`、`effective_capabilities` 等输出拆出可追踪节点

增量采集建议优先支持两种运行模式：

- 目录扫描模式：面向冷启动和全量重建
- `git diff` 模式：面向 PR 合并后、每日增量和本地开发迭代

此外建议显式接入两类工程上下文：

- PR metadata：标题、描述、labels、changed files
- git changeset context：变更文件集合、commit 摘要、base/head 范围

边界：

- 不直接写 `normalized/`
- 不做最终晋升决策

### 8.2 Knowledge Promoter

定位：

- generated 到 normalized 的治理入口 skill

职责：

- 读取候选卡片
- 做 dedupe / merge / conflict detection
- 根据 promotion policy 决定是否晋升
- 生成 merge report
- 写入 `normalized/`
- 更新 `state/promotion_state.json`

核心匹配关系建议显式区分：

- `same_as`: 语义相同，应合并到同一 canonical card
- `supersedes`: 新版本替代旧版本，应晋升新卡并标记旧卡废弃
- `conflicts_with`: 存在冲突，默认不自动晋升

除自动晋升外，还应显式产出：

- review queue：需要人工确认的候选项
- rejected candidates：证据过弱或质量不足的候选项

人工审核回写建议采用结构化 decisions 文件，例如：

```json
{
  "items": [
    {
      "candidate_key": "feature:checkout-flow",
      "action": "approve",
      "note": "approved by product review"
    }
  ]
}
```

边界：

- 不做大规模源扫描
- 不做 graph 构建

## 9. 推荐执行模式

### 9.1 任务闭环触发

当一次需求迭代结束时，执行：

```text
mission-complete
-> knowledge-promoter
```

前提是已有本次任务产出的候选知识。

### 9.2 周期性自动收集

按仓库或团队节奏周期执行：

```text
repo/docs changed
-> knowledge-collector
```

适合：

- 每日增量扫描
- PR 合并后触发
- 版本发布后触发

### 9.3 半自动晋升

对于高价值但高风险的卡片类型，建议由 promoter 先输出报告，再由人确认后晋升。

## 10. 与 Mission 的集成

Mission 推荐消费策略：

- 默认模式：仅消费 `normalized/`
- 增强模式：消费 `normalized/` + 高置信度 `generated/`
- 严格模式：禁止读取 `generated/`

PRD Mission、Design Mission、Coding Mission 等不应直接依赖未治理的候选知识作为强约束。

## 11. 增量状态管理

建议维护以下状态文件：

### 11.1 `state/source_registry.json`

记录：

- 已扫描源
- 最近处理时间
- 对应 hash / revision
- 上次产出 candidate ids

### 11.2 `state/promotion_state.json`

记录：

- candidate 是否已晋升
- 晋升时间
- 晋升目标
- 驳回原因

### 11.3 `state/dedupe_index.json`

记录：

- candidate id 到 canonical id 的映射
- same_as / supersedes 关系

### 11.4 `state/review_decisions.template.json`

作为人工审核输入模板，用于回写：

- `approve`
- `review`
- `reject`

实际审核文件可基于该模板生成，再通过 `knowledge-promoter --review-decisions` 或仓库级 orchestrator 传入。

## 12. 当前落地状态

当前仓库已具备以下首版能力：

- `knowledge-collector`：增量扫描 code / docs / API / ADR / artifacts / PR metadata
- `knowledge-promoter`：执行 dedupe / merge / supersede / conflict detection / review queue
- `rebuild_semantic_index.py`：基于 `normalized/` 重建 `index/`
- `run_knowbase_accumulation.py`：串联 collector -> promoter -> index refresh

当前仍建议继续增强：

- 将该入口进一步接入 mission 终态或 PR merge 自动触发点
- 增强人工审核决策 schema 和协作流程
- 补更细的 card-specific promotion policy

## 13. 推荐落地顺序

建议按以下顺序推进：

1. 固化统一 card 治理字段
2. 实现 `knowledge-collector`
3. 实现 `knowledge-promoter`
4. 建立 `generated/` 与 `normalized/` 的晋升契约
5. 补齐 dedupe / merge report
6. 接入定时自动收集

## 14. 最终结论

Knowbase 的积累不应被拆成互不相干的两套机制，而应理解为：

```text
两种入口
+ 两种置信度
+ 一套统一晋升机制
= 一份正式 Knowbase
```

因此，推荐的系统实现是：

- 用 `knowledge-collector` 承接自动收集
- 用 `knowledge-promoter` 承接正式沉淀与晋升
- 用 `generated/ -> normalized/` 的明确边界保证知识质量

这能同时满足规模化自动沉淀与工程级知识可信度两方面要求。
