---
name: context-build
description: >
  PRD Mission 流水线第二阶段：上下文构建 + 摘要压缩。
  在 prd-intake skill 输出 intake_result.json（status=proceed）后触发。
  运行 4 个知识检索脚本，再由 Claude 做上下文摘要压缩，
  输出 context_summary.json 供后续 platform-review / prd-compile 使用。
---

# Context Build Skill

## 职责

从 Knowbase 中按需检索与当前需求相关的知识卡（Feature / Rule / Capability / Playbook），
通过图谱扩展关联节点，再经过 Resolver 过滤聚合，最终压缩为结构化 context_summary.json。

本 skill 分两步：
1. **脚本层**（确定性处理）：4 个脚本按序执行，完成知识检索 → 图谱扩展 → 规则解析 → 能力解析
2. **推理层**（Claude 摘要）：将脚本输出压缩为 context_summary.json，控制 token 上限

---

## 前置条件

- 已有 `intake_result.json`（status=proceed）
- 已有 `repo_profile.yaml`（提供 repo_id / platform / domain 等上下文）
- 已有 Knowbase 目录结构（`company-knowbase/` 或 `knowledge/`）

读取 `repo_profile.yaml` 获取以下字段，用于后续脚本调用：
```yaml
repo_id: "..."
platform: "backend"          # 当前 repo 主平台
domain: ["payment", "order"] # 业务领域
global_knowbase_path: "../company-knowbase"
local_rules_path: "./knowledge/rules/local"
local_capabilities_path: "./knowledge/capabilities/local"
```

---

## 步骤一：运行知识检索脚本

### 1.1 retrieve_knowledge.py
从 Knowbase 中检索与需求相关的知识卡，含 Playbook 匹配。

```bash
python scripts/retrieve_knowledge.py \
  --input artifacts/prd/<feature_id>/v<N>/intake_result.json \
  --knowledge-root <global_knowbase_path> \
  --output artifacts/prd/<feature_id>/v<N>/context_candidates.json
```

输出包含：`feature_cards`（最多10）、`rule_cards`（最多20）、`capability_cards`（最多15）、`playbook_cards`（最多5）

### 1.2 expand_relations.py
通过 `edges.json` 图谱，扩展与 seed 卡片相关联的卡片（1-hop）。
边类型范围：`depends_on / conflicts_with / supersedes / related_to / implements / required_by`

```bash
python scripts/expand_relations.py \
  --input artifacts/prd/<feature_id>/v<N>/context_candidates.json \
  --knowledge-root <global_knowbase_path> \
  --output artifacts/prd/<feature_id>/v<N>/context_expanded.json
```

### 1.3 resolve_rules.py
从 global + local 规则库中，按 stage / scope / 相关性过滤并 override，输出有效规则。
**关键**：repo 规则 > platform 规则 > global 规则，同主题规则按 specificity 显式覆盖。

```bash
python scripts/resolve_rules.py \
  --input <(echo '{"stage":"prd","platform":"<platform>","repo_id":"<repo_id>","keywords":[...],"domains":[...],"feature_ids":[...]}') \
  --global-root <global_knowbase_path> \
  --local-root ./knowledge \
  --output artifacts/prd/<feature_id>/v<N>/effective_rules.json
```

> 从 intake_result.json 中提取 `keywords`（来自 summary/domains）、`domains`、`feature_ids`；
> `platform` 和 `repo_id` 从 `repo_profile.yaml` 读取。

### 1.4 resolve_capabilities.py
从 global + local capability 库中，按相关性排序，ready 优先，输出有效能力。

```bash
python scripts/resolve_capabilities.py \
  --input <(echo '{"stage":"prd","platform":"<platform>","keywords":[...],"domains":[...],"feature_ids":[...]}') \
  --global-root <global_knowbase_path> \
  --local-root ./knowledge \
  --output artifacts/prd/<feature_id>/v<N>/effective_capabilities.json
```

---

## 步骤二：执行 Context 摘要压缩（Claude 推理）

读取以下四个文件，压缩为 context_summary.json：
- `context_expanded.json`（feature / rule / capability / playbook 候选卡）
- `effective_rules.json`（经过 override 后的有效规则）
- `effective_capabilities.json`（按相关性排序的有效能力）
- `intake_result.json`（task_type / affected_platforms / domains）

### Token 阈值（v3 §8.3）

| 字段 | 最大条数 | 每条建议摘要长度 |
|------|----------|----------------|
| related_features | 10 | ≤150字 |
| relevant_rules | 20 | ≤100字，critical 优先 |
| available_capabilities | 15 | ≤100字 |
| platform_constraints | 10 | ≤80字 |
| open_risks | 8 | ≤100字，blocker 优先 |

超出条数按相关性截断，每条内容超长时只保留 summary 字段。

### 摘要要点

- `related_features`：与当前需求功能相关的已有功能，重点关注 depends_on / implements 关系
- `relevant_rules`：过滤后的有效规则，priority=critical 必须全量包含
- `available_capabilities`：可复用的已有系统能力，availability=ready 优先
- `platform_constraints`：从 rule_cards 和 capability_cards 中识别平台特有的约束
- `open_risks`：识别跨端冲突、缺失能力、规则冲突等潜在风险

### 透传字段（供下游使用，不做摘要）

```json
{
  "playbook_cards": [...],          // 来自 context_expanded.json
  "affected_platforms": [...],      // 来自 intake_result.json
  "effective_rules": [...]          // 来自 effective_rules.json（供 validate_final_prd 校验）
}
```

### 输出格式

写入 `artifacts/prd/<feature_id>/v<N>/context_summary.json`：

```json
{
  "related_features": [...],
  "relevant_rules": [...],
  "available_capabilities": [...],
  "platform_constraints": [...],
  "open_risks": [...],
  "playbook_cards": [...],
  "affected_platforms": [...],
  "effective_rules": [...]
}
```

---

## 下游流程决策

输出 context_summary.json 后，检查触发条件决定下一步：

**触发 platform-review skill 的条件**（满足任一）：
- `open_risks` 数量 > 0
- `platform_constraints` 数量 > 0
- `intake_result.task_type` 为 `new_feature` 或 `breaking_change`
- `affected_platforms` 数量 > 1

若不满足，跳过 platform-review，直接进入 **prd-compile** skill。

---

## Artifacts 输出清单

| 文件 | 产出方 |
|------|--------|
| `context_candidates.json` | retrieve_knowledge.py |
| `context_expanded.json` | expand_relations.py |
| `effective_rules.json` | resolve_rules.py |
| `effective_capabilities.json` | resolve_capabilities.py |
| `context_summary.json` | Claude 推理 |
