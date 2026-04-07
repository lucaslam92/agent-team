# PRD Mission 设计文档（v3）

> **版本说明**：本文档在 v2 基础上修复了以下问题：
> 流程早退出机制缺失 / 条件节点触发条件未定义 / Playbooks 职责悬空 /
> platform-feasibility-review 单 Skill 负载过重 / token 阈值未量化 /
> repo_profile.yaml 未定义 / validate_final_prd.py 校验标准不明确 /
> 缺少 human-in-the-loop 回路 / 知识图谱边类型未定义 / 缺少版本追踪机制

---

## 1. 目标

构建一个自动化 PRD 系统，实现：

> 输入需求 → 自动理解 → 补充上下文 → 多端评估 → 架构收敛 → 输出可执行 PRD

**系统目标：**

- 支持多源输入（Jira / Doc / 文本）
- 自动判断需求是否完整
- 自动结合历史业务（Knowbase）
- 自动做多端可行性评估
- 自动做架构决策
- 输出结构化 PRD（供 Design / Coding 使用）

---

## 2. 核心架构

系统采用三层架构：

| 层级 | 类型 | 职责 |
|------|------|------|
| 推理层 | Skill | 分类 / 收敛 / 决策 / 生成 |
| 确定性处理层 | Script | 解析 / 检索 / 聚合 / 校验 |
| 外部数据层 | MCP | Jira / Doc / Sheet / Figma 数据获取 |

---

## 3. 执行流程（v3 完整版）

### 3.1 流程总图

```
用户输入
│
├─► resolve_input.py → input_ref.json
│
├─► [MCP] fetch source → raw_source.json
│
├─► normalize_source.py → normalized_input.json
│
├─► [MCP + scripts] resolve_resources → resource_index.json
│
├─► prd-intake-check → intake_result.json
│       │
│       ├─[blocked]──────────────────────────────────────► ★ EARLY EXIT
│       │                                                   输出 blocked 终态
│       │                                                   → 进入 human-in-the-loop 回路
│       │
│       └─[skip_prd]──────────────────────────────────────► ★ EARLY EXIT
│                                                           输出 skip_prd 终态
│
├─► retrieve_knowledge.py → context_candidates.json
│
├─► expand_relations.py → context_expanded.json
│
├─► resolve_rules.py → effective_rules.json
│
├─► resolve_capabilities.py → effective_capabilities.json
│
├─► context-summarize → context_summary.json
│
├─► [conditional] platform-feasibility-review
│       触发条件见 §3.2
│       → platform_review.json
│
├─► [conditional] architect-converge
│       触发条件见 §3.3
│       → architect_decision.json
│
├─► final-prd-compile → final_prd.json
│
├─► validate_final_prd.py → final_prd_validation.json
│       │
│       └─[invalid]──────────────────────────────────────► ★ EARLY EXIT（重新进入 compile）
│
├─► [optional] semantic-gate-check
│       触发条件见 §3.4
│       → semantic_gate_result.json
│
└─► mission_result.json（ready 终态）
```

### 3.2 platform-feasibility-review 触发条件

当 `context_summary.json` 中满足以下**任一**条件时，触发该步骤：

```json
{
  "trigger_conditions": [
    "open_risks 数量 > 0",
    "platform_constraints 数量 > 0",
    "intake_result.task_type 为 new_feature 或 breaking_change",
    "intake_result.affected_platforms 数量 > 1"
  ]
}
```

若均不满足（如纯文案修改、配置变更等），跳过此步骤，`platform_review.json` 置为空对象 `{}`。

### 3.3 architect-converge 触发条件

当 `platform_review.json` 中满足以下**任一**条件时，触发该步骤：

```json
{
  "trigger_conditions": [
    "存在跨端冲突（cross_platform_conflicts 数量 > 0）",
    "存在 blocker 级别风险（risk_level = blocker）",
    "存在多个 effective_rules 互相冲突"
  ]
}
```

若不满足，跳过此步骤，`architect_decision.json` 置为空对象 `{}`。

### 3.4 semantic-gate-check 触发条件

当满足以下**任一**条件时，触发该步骤：

```json
{
  "trigger_conditions": [
    "intake_result.task_type 为 breaking_change",
    "effective_rules 中存在 priority=critical 的规则",
    "final_prd 涉及核心支付 / 权限 / 安全模块"
  ]
}
```

---

## 4. Human-in-the-Loop 回路（新增）

### 4.1 触发场景

| 场景 | 来源节点 | 回路入口 |
|------|----------|----------|
| 需求信息不完整 | prd-intake-check → blocked | 用户补充后，从 normalize_source.py 重新进入 |
| PRD 校验不通过 | validate_final_prd.py → invalid | 自动修复失败后，回到 final-prd-compile |
| 架构决策需人工确认 | architect-converge 输出 needs_human_review | 等待人工决策后继续 |

### 4.2 blocked 回路设计

```
mission_result.json（blocked）
  └── missing_info: ["缺少目标用户定义", "缺少性能 SLA"]
        │
        └── 向用户呈现 missing_info 列表，请求补充
              │
              └── 用户提交补充信息
                    │
                    └── 重新进入 normalize_source.py（携带原始 input + 补充信息）
                          └── 继续正常流程
```

**补充输入合并规则：**

```python
# normalize_source.py 合并逻辑
merged_input = {
    **original_normalized_input,
    **supplemental_input,
    "_revision": original_normalized_input.get("_revision", 0) + 1
}
```

### 4.3 validate 失败回路设计

```
final_prd_validation.json（invalid）
  └── validation_errors: [...]
        │
        ├── [可自动修复] → 重新调用 final-prd-compile（携带 validation_errors 作为修复指令）
        │                   最多重试 2 次
        │
        └── [无法自动修复] → 返回 blocked 终态，标注 validation_errors
```

---

## 5. Knowbase 设计

### 5.1 分层模型

```
Global（业务层）
  └── Platform（平台层）
        └── Repo（本地层）
```

### 5.2 知识类型

| 类型 | 描述 |
|------|------|
| Feature Card | 业务功能定义 |
| Rule Card | 业务规则 / 平台规则 / 工程规则 |
| Capability Card | 已有系统能力 |
| Playbook | 面向特定场景的执行策略模板（详见 §5.5） |

### 5.3 中心仓库结构

```
company-knowbase/
  normalized/
    features/
    capabilities/
    rules/
      business/
      platform/
    playbooks/
  index/
    nodes.json
    edges.json
```

### 5.4 本地 repo 结构

```
/
  knowledge/
    rules/local/
    capabilities/local/
    playbooks/local/
  repo_profile.yaml
```

### 5.5 Playbook 职责（v2 遗留问题修复）

Playbook 是面向特定业务场景的**执行策略模板**，用于在 `prd-intake-check` 分类后，为特定 task_type 注入已验证的处理策略。

**使用时机：** `prd-intake-check` 输出 `task_type` 后，`retrieve_knowledge.py` 会检索与该 task_type 匹配的 Playbook，作为 `context_candidates.json` 的一部分传入后续流程。

**Playbook 字段示例：**

```json
{
  "playbook_id": "pb_payment_feature",
  "task_types": ["new_feature", "breaking_change"],
  "domains": ["payment"],
  "steps_hint": [
    "必须包含支付降级方案",
    "必须经过安全团队 review",
    "必须定义幂等键设计"
  ],
  "required_sections_in_prd": [
    "fallback_strategy",
    "idempotency_design",
    "security_review_checklist"
  ]
}
```

### 5.6 Rule Card 关键字段

```json
{
  "rule_id": "",
  "priority": "critical | high | normal",
  "scope": {
    "level": "global | platform | repo",
    "platform": "",
    "repo": ""
  },
  "stage": ["prd", "design", "coding"],
  "content": "",
  "supersedes": []
}
```

### 5.7 规则优先级

```
repo > platform > global
```

### 5.8 知识图谱边类型（v2 遗留问题修复）

`edges.json` 中每条边必须包含 `type` 字段，支持以下类型：

| 边类型 | 含义 | 示例 |
|--------|------|------|
| `depends_on` | A 依赖 B | Feature A 依赖 Capability B |
| `conflicts_with` | A 与 B 存在冲突 | Rule A 与 Rule B 互斥 |
| `supersedes` | A 覆盖 B | Repo Rule A 覆盖 Global Rule B |
| `related_to` | 弱关联 | Feature A 与 Feature B 相关 |
| `implements` | A 实现 B | Capability A 实现 Feature B |
| `required_by` | A 被 B 依赖 | Rule A 被 Playbook B 引用 |

**edges.json 示例：**

```json
[
  {
    "from": "rule_payment_idempotency",
    "to": "rule_global_api_standard",
    "type": "supersedes",
    "scope": "repo"
  },
  {
    "from": "feature_checkout",
    "to": "capability_payment_sdk",
    "type": "depends_on"
  }
]
```

---

## 6. repo_profile.yaml 定义（v2 遗留问题修复）

`repo_profile.yaml` 是 Resolver 识别当前 repo 归属、适用规则和上下文范围的入口文件。

```yaml
# repo_profile.yaml

repo_id: "order-service"           # 唯一标识，全局不重复
platform: "backend"                # android | ios | web | backend | cross
domain: ["payment", "order"]       # 业务领域，用于规则和 capability 过滤
team: "platform-team"              # 归属团队
knowbase_version: "2.1.0"          # 使用的 Knowbase 版本，用于缓存校验
global_knowbase_path: "../company-knowbase"  # 相对或绝对路径
local_rules_path: "./knowledge/rules/local"
local_capabilities_path: "./knowledge/capabilities/local"
local_playbooks_path: "./knowledge/playbooks/local"

# 可选：明确声明继承的 platform profile
inherits_platform_profile: "backend-java"
```

Resolver 在初始化时读取此文件，建立 `{repo_id, platform, domain}` 三元组，用于后续所有过滤和打分。

---

## 7. Resolver 设计

### 7.1 Rule Resolver

**输入：**

```json
{
  "stage": "prd",
  "platform": "backend",
  "repo_id": "order-service",
  "keywords": [],
  "domains": ["payment"],
  "feature_ids": []
}
```

**输出：**

```json
{
  "effective_rules": [],
  "override_trace": []
}
```

**核心逻辑：**

1. 加载 global / platform / repo 规则
2. 按 `stage` 过滤
3. 按 `scope`（platform / domain）过滤
4. 按相关性打分（keyword + domain + feature_id 匹配）
5. 执行 override（repo > platform > global），记录 `override_trace`
6. 截断至最多 **20 条**（按 priority 降序）
7. 输出 `effective_rules`

### 7.2 Capability Resolver

**输入：** 同 Rule Resolver

**输出：**

```json
{
  "effective_capabilities": []
}
```

**核心逻辑：**

1. 加载 global + local capability
2. 按 feature / domain / keyword 打分
3. 优先选择 `availability=ready`
4. 截断至最多 **15 条**（按打分降序）

---

## 8. Context Enrichment

### 8.1 组成

| Script/Skill | 输出 |
|---|---|
| retrieve_knowledge.py | context_candidates.json |
| expand_relations.py | context_expanded.json |
| resolve_rules.py | effective_rules.json |
| resolve_capabilities.py | effective_capabilities.json |
| context-summarize | context_summary.json |

### 8.2 输出（核心结构）

```json
{
  "related_features": [],
  "relevant_rules": [],
  "available_capabilities": [],
  "platform_constraints": [],
  "open_risks": []
}
```

### 8.3 Token 阈值（v2 遗留问题修复）

| 字段 | 最大条数 | 每条最大 token |
|------|----------|----------------|
| related_features | 10 | 300 |
| relevant_rules | 20 | 200 |
| available_capabilities | 15 | 200 |
| platform_constraints | 10 | 150 |
| open_risks | 8 | 200 |

`context-summarize` Skill 负责在上述阈值内做最终压缩，超出部分按相关性分数截断。

### 8.4 设计原则

- 按需检索（不预加载）
- 按阈值截断（防止 token 爆炸）
- context-summarize 只输出摘要，不传递原始 chunk

---

## 9. Skill 体系

### 9.1 prd-intake-check

**职责：** task 分类 / requirement 提取 / completeness 检查

**输出关键字段：**

```json
{
  "task_type": "new_feature | enhancement | bug_fix | breaking_change | config_change | skip_prd",
  "affected_platforms": ["backend", "ios"],
  "completeness": "complete | incomplete",
  "missing_info": [],
  "status": "proceed | blocked | skip_prd"
}
```

### 9.2 context-summarize

**职责：** 压缩 Feature / Rule / Capability，输出 context_summary

### 9.3 platform-feasibility-review（v2 问题修复：拆分视角）

**职责：** 多端可行性分析，输出风险与阻塞问题

**内部执行策略（视角分治）：**

为避免单 Skill 同时处理四端导致推理质量下降，该 Skill 内部采用以下策略：

1. **Phase 1（各端独立分析）：** 对 `affected_platforms` 中的每个平台，依次独立推理，各自输出风险列表
2. **Phase 2（跨端收敛）：** 在 Phase 1 结果基础上，做跨端冲突识别与优先级排序

每次只激活当前 repo 的 `affected_platforms`，不注入无关端的 context。

**输出结构：**

```json
{
  "per_platform_risks": {
    "backend": [],
    "ios": []
  },
  "cross_platform_conflicts": [],
  "blockers": [],
  "warnings": []
}
```

### 9.4 architect-converge

**职责：** 收敛冲突 / 输出最终决策 / 消灭不确定性

**输出结构：**

```json
{
  "decisions": [],
  "resolved_conflicts": [],
  "needs_human_review": false,
  "human_review_reason": ""
}
```

> 当 `needs_human_review: true` 时，流程进入 human-in-the-loop 回路（见 §4）。

### 9.5 final-prd-compile

**职责：** 输出最终结构化 PRD

### 9.6 semantic-gate-check（可选）

**职责：** 语义一致性校验，确保 PRD 各节之间无逻辑矛盾

---

## 10. Script 体系

| Script | 职责 |
|--------|------|
| resolve_input.py | 解析多源输入，输出 input_ref.json |
| normalize_source.py | 标准化 raw_source，支持多轮输入合并（含 _revision 字段） |
| resolve_resources.py | 协调 MCP 调用，聚合外部资源 |
| retrieve_knowledge.py | 按需检索 Knowbase，含 Playbook 匹配 |
| expand_relations.py | 图谱遍历，按边类型扩展关联节点 |
| resolve_rules.py | 调用 Rule Resolver，输出 effective_rules |
| resolve_capabilities.py | 调用 Capability Resolver，输出 effective_capabilities |
| validate_final_prd.py | PRD 校验（见 §10.1） |

### 10.1 validate_final_prd.py 校验标准（v2 遗留问题修复）

校验分为三个层次，按顺序执行：

**Layer 1：Schema 合规性**
- final_prd.json 符合预定义 JSON Schema
- 所有必填字段存在且非空

**Layer 2：完整性校验**
- Playbook 要求的 `required_sections_in_prd` 全部存在
- `affected_platforms` 中每个平台均有对应的实现方案章节

**Layer 3：规则合规性校验**
- `priority=critical` 的 effective_rules 在 PRD 中均有体现
- 无被 override 的低优先级规则出现在 PRD 中（防止 Resolver override 失效）

> **与 semantic-gate-check 的边界：**
> `validate_final_prd.py` 做结构性和规则性校验（确定性逻辑）；
> `semantic-gate-check` 做语义一致性校验（推理逻辑，如"目标与方案是否一致"）。

---

## 11. Artifact 体系

```
artifacts/prd/
  {feature_id}/
    v{revision}/
      input_ref.json
      raw_source.json
      normalized_input.json
      resource_index.json
      intake_result.json
      context_candidates.json
      context_expanded.json
      effective_rules.json
      effective_capabilities.json
      context_summary.json
      platform_review.json
      architect_decision.json
      final_prd.json
      final_prd_validation.json
      semantic_gate_result.json
      mission_result.json
    latest -> v{revision}/   # 符号链接，指向最新版本
```

> **版本追踪（v2 遗留问题修复）：**
> 每次触发 PRD Mission 均生成新的 `v{revision}` 子目录。
> `mission_result.json` 中记录 `previous_version` 字段，便于 diff 和回溯。

**mission_result.json 版本字段：**

```json
{
  "status": "ready",
  "version": "v3",
  "previous_version": "v2",
  "final_prd_path": "artifacts/prd/feature_checkout/v3/final_prd.json",
  "diff_summary": "新增幂等键设计章节；移除旧版降级方案"
}
```

---

## 12. 分阶段知识使用策略

| 阶段 | Rules | Capabilities | Playbooks |
|------|-------|--------------|-----------|
| PRD | business rules（核心）/ platform rules（少量） | backend capability（核心） | 匹配 task_type 的 Playbook |
| Design | business + platform + repo rules | capability（更重） | UI/UX 相关 Playbook |
| Coding | repo rules（优先）/ business rules（补充） | local capability（优先） | 工程规范 Playbook |

---

## 13. 终态输出

**ready：**

```json
{
  "status": "ready",
  "version": "v3",
  "previous_version": "v2",
  "final_prd_path": "",
  "diff_summary": ""
}
```

**blocked：**

```json
{
  "status": "blocked",
  "missing_info": [],
  "validation_errors": [],
  "next_action": "请补充 missing_info 后重新提交"
}
```

**skip_prd：**

```json
{
  "status": "skip_prd",
  "reason": ""
}
```

---

## 14. 关键设计原则

1. **Knowbase ≠ 文档系统**：必须结构化（JSON/YAML），所有节点可被程序化检索
2. **Skill ≠ 数据处理**：Skill 只做推理，所有确定性逻辑归 Script
3. **Resolver ≠ 推理**：Resolver 只做聚合与过滤，不做语义判断
4. **上下文按需注入，按阈值截断**：避免 token 浪费，见 §8.3
5. **单 Skill 多视角，内部分治**：platform-feasibility-review 内部分阶段执行，而非多 Agent
6. **所有条件分支必须有明确触发条件**：见 §3.2 / §3.3 / §3.4
7. **Human-in-the-loop 是一等公民**：blocked / needs_human_review 均有明确回路
8. **版本不可变**：每次运行生成独立版本目录，支持 diff 和回溯

---

## 15. 系统本质

```
Requirement
  → Understanding（prd-intake-check）
  → Context Injection（Knowbase + Resolver + Context Enrichment）
  → Feasibility Analysis（platform-feasibility-review）
  → Decision（architect-converge）
  → Contract（final-prd-compile → validate）
```

---

## 16. 一句话总结

> **PRD Mission 是一个"AI PM + Tech Lead + Architect"的组合系统，通过 Knowbase + Resolver + Skill 协同，配合明确的条件分支、human-in-the-loop 回路和版本追踪机制，实现从需求到可执行 PRD 的自动化闭环。**

---

## 17. 向 AI Software Engineering System 演进

PRD Mission 不是孤立存在的单一流程，它应作为更大系统中的一个 Mission 节点，纳入统一的软件工程架构中。

目标演进方向：

```text
原始输入
-> 知识抽取
-> 图结构
-> 语义建模
-> 工程决策
-> 自动执行
```

最终覆盖完整研发流程：

- PRD
- Design
- Coding
- Verification
- PR

从这个视角看，PRD Mission 是整个 AI Software Engineering System 在需求阶段的入口实现。

---

## 18. 系统级四层架构（补充）

在 PRD Mission 现有三层实现基础上，建议向系统级四层架构收敛：

- Layer 0: Raw Layer
- Layer 1: Graph Layer
- Layer 2: Semantic Layer（Knowbase）
- Layer 3: Execution Layer（Mission）

### 18.1 Layer 0：Raw Layer

Raw Layer 负责承接所有未经统一建模的原始输入，包括：

- PRD
- Code
- API
- Docs
- Jira
- Figma
- Logs

特点：

- 无结构
- 多来源
- 可能冲突

该层只保留事实，不做复杂语义解释。

### 18.2 Layer 1：Graph Layer

Graph Layer 的目标是把多源 signals 统一转化为知识图谱：

`signals -> nodes + edges`

核心数据结构：

`nodes.json`

```json
{
  "id": "",
  "type": "code | doc | api | concept",
  "content": "",
  "source": ""
}
```

`edges.json`

```json
{
  "source": "",
  "relation": "calls | depends_on | related_to",
  "target": ""
}
```

核心脚本：

- `extract_android_code.py`
- `extract_web_code.py`
- `extract_backend_code.py`
- `merge_code_signals.py`
- `build_graph.py`

Graph 构建流程：

```text
code/doc
-> extract
-> signals
-> build_graph
-> nodes + edges
```

Graph Retrieval 是这里的关键能力：

```text
query -> seed nodes -> k-hop expansion -> subgraph
```

这将替代纯 keyword 检索。

### 18.3 Layer 2：Semantic Layer（Knowbase）

语义层负责把 Graph 中的结构事实提升为稳定、可复用的语义知识。

知识类型包括：

- Feature Card
- Rule Card
- Capability Card
- Playbook Card
- Capacity Profile Card

建议目录结构：

```text
company-knowbase/
  normalized/
    features/
    rules/
      business/
      platform/
      engineering/
    capabilities/
    capacity/
    playbooks/
  generated/
  index/
    nodes.json
    edges.json
```

生成流程：

```text
graph
-> code-to-knowledge-interpreter
-> normalize
-> dedupe
-> persist
-> index
```

核心脚本：

- `normalize_extracted_cards.py`
- `dedupe_generated_cards.py`
- `persist_generated_cards.py`
- `rebuild_knowledge_index.py`

### 18.4 Layer 3：Execution Layer（Mission）

Mission 层负责把 Knowbase 和 Resolver 的结果转成真实的工程动作。

建议 Mission 体系：

- PRD Mission
- Design Mission
- Coding Mission
- Verification Mission
- PR Mission

PRD Mission 只是其中一个入口 Mission。

---

## 19. Graph 替换检索与 Interpreter（补充）

### 19.1 检索路径升级

当前 PRD Mission 的上下文构建链路仍以 `retrieve_knowledge.py` 为主入口。建议逐步替换为：

```text
graph -> subgraph -> interpreter -> cards
```

替代原方案：

```text
keyword search -> cards
```

在 PRD Mission 中，Context Enrichment 应升级为：

```text
graph_retrieve
-> resolve_rules
-> resolve_capabilities
-> context_summary
```

即：

- `retrieve_knowledge` 逐步废弃
- `graph_retrieve` 成为唯一推荐入口

### 19.2 Interpreter 定位

新增核心组件：

`code-to-knowledge-interpreter`

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

职责：

- 合并多端信号
- 推断业务 Feature
- 提升 Rule（business / engineering）
- 统一 Capability
- 建立依赖关系

边界：

- LLM 只做语义提升
- 不做 extract / persist / dedupe / index
- 确定性处理必须由脚本承担

### 19.3 graph-aware resolver

Resolver 也需要升级为 graph-aware 版本：

- `resolve_rules` 不再只依赖 keyword / domain
- `resolve_capabilities` 需消费 `subgraph.json`
- 排序应综合考虑 graph proximity、domain、availability

建议排序函数：

```text
graph_score * 0.5 + domain_score * 0.3 + availability_score * 0.2
```

---

## 20. 架构同步机制（补充）

### 20.1 `architecture_state.json`

系统级建议新增统一架构状态文件，作为多层协同的单一事实源：

```json
{
  "version": "1.0",
  "layers": {
    "raw": { "enabled": true },
    "graph": {
      "enabled": true,
      "retrieval": "k-hop",
      "default_hops": 2,
      "max_nodes": 200,
      "allowed_relations": ["calls", "depends_on", "related_to", "implements", "owned_by"]
    },
    "semantic": {
      "enabled": true,
      "knowbase_root": "company-knowbase",
      "card_types": ["feature", "rule", "capability", "playbook", "capacity"],
      "dedupe": true
    },
    "execution": {
      "enabled": true,
      "missions": ["prd", "design", "coding", "verification", "pr"]
    }
  },
  "resolver": {
    "rule_priority": ["repo", "platform", "global"],
    "capability_priority": ["feature_match", "domain_match", "availability"],
    "graph_required": true
  },
  "policies": {
    "forbid_keyword_retrieval": true,
    "require_adr_alignment": true,
    "require_architecture_sync": true
  }
}
```

约束：

- 所有 Mission 执行前必须读取该文件
- 不允许 silently fallback 到 keyword retrieval
- 架构变更需先更新该文件，再更新实现

### 20.2 ADR（必须）

系统级 ADR 路径建议统一为：

`docs/adr/`

首批建议包含：

- ADR-001: 引入 Graph Layer
- ADR-002: Knowbase Schema
- ADR-003: Interpreter 机制

### 20.3 Claude Code / Claude CLI 使用约束

新的系统能力需要考虑可被 Claude Code 或 Claude CLI 直接消费，并优先采用标准 Claude skill 方式实现，而不是依赖仓库私有运行约定。

实现约束应明确：

- 必须使用标准 Claude skill 目录结构组织能力
- 每个 skill 至少包含 `SKILL.md`
- 仅在需要时增加 `scripts/`、`references/`、`assets/`
- `SKILL.md` 的 `description` 必须承担触发职责，清楚描述 skill 做什么、何时使用
- 必须使用 graph retrieval
- 不得使用 keyword retrieval 作为主路径
- 必须遵循 `architecture_state.json`
- 必须遵循 ADR

建议的标准 skill 组织方式：

```text
<skill-name>/
  SKILL.md
  scripts/        # 可选，确定性处理
  references/     # 可选，按需加载
  assets/         # 可选，输出资源
```

对于 Claude Code / Claude CLI：

- Skill 应尽量保持自描述和自包含
- Script 应可直接通过 CLI 调用
- 不应把运行前提绑定到 Codex 私有元数据或 UI 配置
- Mission 编排应由 skill 之间的清晰输入输出契约驱动

---

## 21. 推荐实施顺序（补充）

具体待补功能、优先级和实施 backlog 不再维护在设计文档中，统一迁移到独立 TODO 文件：

[`docs/AI_Software_Engineering_System_TODO.md`](./AI_Software_Engineering_System_TODO.md)

设计文档仅保留目标架构、原则、边界和演进方向；执行清单、缺口盘点和推进顺序统一在 TODO 文件中维护。

---

## 22. 系统级结论（补充）

PRD Mission 的下一阶段，不只是继续细化 PRD 流程本身，而是把它纳入完整的软件工程系统：

```text
Graph（连接）
+ Semantic（语义）
+ Mission（执行）
= AI Software Engineering System
```

从系统建设优先级看，最关键的分水岭仍然是：

- `build_graph.py`
- `graph_retrieve.py`
- graph-aware resolver

这是从“PRD 自动化”升级到“知识驱动的软件工程操作系统”的关键一步。
