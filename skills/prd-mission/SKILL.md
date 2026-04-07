---
name: prd-mission
description: >
  PRD Mission 流水线的统一入口和编排层。
  当用户提供一个需求（Jira / Doc / 文本）并希望自动生成结构化 PRD 时使用此 skill。
  负责初始化运行上下文（feature_id / version）、按条件调用各阶段 skill、
  管理所有早退出和 human-in-the-loop 分支，最终输出 mission_result.json。
---

# PRD Mission — 主编排 Skill

## 一、启动前：初始化运行上下文

在调用任何子 skill 之前，先确定本次运行的两个关键参数：

### feature_id（功能标识）

按以下优先级确定：
1. 若用户输入是 Jira key（如 `ORDER-123`）→ `feature_id = "ORDER-123"`
2. 若用户输入是 GDoc / Confluence URL → `feature_id = <URL中的文档ID后8位>`
3. 若用户输入是纯文本 → 从文本中提取关键名词生成 slug（如 "添加支付回调重试" → `feature_id = "payment-callback-retry"`）
4. 若用户已明确指定 → 直接使用

### version（运行版本号）

```
artifacts_dir = artifacts/prd/<feature_id>/
如果该目录不存在   → version = "v1"，revision = 0
如果已存在 v1/     → version = "v2"，revision = 1
如果已存在 v1/ v2/ → version = "v3"，revision = 2
以此类推
```

> 所有后续步骤的 artifact 路径统一为：`artifacts/prd/<feature_id>/<version>/`
> 创建该目录：`mkdir -p artifacts/prd/<feature_id>/<version>/`

---

## 二、完整执行流程

```
用户输入
    │
    ▼
【初始化】确定 feature_id + version，创建 artifact 目录
    │
    ▼
【Stage 1】prd-intake skill
    │   输出: intake_result.json
    │
    ├─ status=skip_prd ──────────────────────────────► [终态] SKIP_PRD
    ├─ status=blocked  ──────────────────────────────► [暂停] 等待用户补充 → 重跑 Stage 1
    └─ status=proceed
         │
         ▼
【Stage 2】context-build skill
    │   输出: context_summary.json
    │
    │   检查触发条件（满足任一 → 执行 Stage 3，否则跳过）：
    │     · open_risks > 0
    │     · platform_constraints > 0
    │     · task_type ∈ {new_feature, breaking_change}
    │     · affected_platforms 数量 > 1
    │
    ├─ 不满足 ──────────────────────────────────────► 跳至 Stage 5
    └─ 满足
         │
         ▼
【Stage 3】platform-review skill
    │   输出: platform_review.json
    │
    │   检查触发条件（满足任一 → 执行 Stage 4，否则跳过）：
    │     · cross_platform_conflicts > 0
    │     · blockers > 0
    │     · effective_rules.json 的 override_trace 中存在 critical 规则被覆盖
    │
    ├─ 不满足 ──────────────────────────────────────► 跳至 Stage 5
    └─ 满足
         │
         ▼
【Stage 4】architect-converge skill
    │   输出: architect_decision.json
    │
    ├─ needs_human_review=true ──────────────────────► [暂停] 等待用户架构决策 → 补充后继续 Stage 5
    └─ needs_human_review=false
         │
         ▼
【Stage 5】prd-compile skill（attempt=1）
    │   输出: final_prd.json + final_prd_validation.json
    │
    ├─ validation=invalid, can_auto_fix=true
    │    └─ attempt < 3 → 重跑 Stage 5（attempt+1，携带 validation_errors）
    │    └─ attempt ≥ 3 → [暂停] blocked，等待用户介入
    │
    ├─ validation=invalid, can_auto_fix=false ──────► [暂停] blocked，展示 issues
    │
    └─ validation=valid
         │
         │   检查触发条件（满足任一 → 执行 Stage 6，否则跳过）：
         │     · task_type = breaking_change
         │     · effective_rules 中存在 priority=critical 的规则
         │     · PRD 涉及 payment/auth/permission/security 域
         │
         ├─ 不满足 ──────────────────────────────────► 跳至终态
         └─ 满足
              │
              ▼
【Stage 6】semantic-gate skill
    │   输出: semantic_gate_result.json
    │
    ├─ status=failed
    │    ├─ 问题可在 PRD 层修复 → 重跑 Stage 5（携带 semantic_issues，attempt 计数独立）
    │    └─ 问题需重新收集需求 → [暂停] 回到 Stage 1（revision+1）
    └─ status=passed / skipped
         │
         ▼
【终态】写入 mission_result.json
```

---

## 三、Artifact 路径约定

所有 artifact 统一存放在 `artifacts/prd/<feature_id>/<version>/` 下：

```
artifacts/prd/<feature_id>/<version>/
├── input_ref.json              (Stage 1 - resolve_input.py)
├── raw_source.json             (Stage 1 - MCP 或 fallback 构造)
├── normalized_input.json       (Stage 1 - normalize_source.py)
├── resource_index.json         (Stage 1 - resolve_resources.py)
├── intake_result.json          (Stage 1 - Claude 推理)
├── context_candidates.json     (Stage 2 - retrieve_knowledge.py)
├── context_expanded.json       (Stage 2 - expand_relations.py)
├── effective_rules.json        (Stage 2 - resolve_rules.py，含 override_trace)
├── effective_capabilities.json (Stage 2 - resolve_capabilities.py)
├── context_summary.json        (Stage 2 - Claude 推理)
├── platform_review.json        (Stage 3 - Claude 推理，跳过时为 {})
├── architect_decision.json     (Stage 4 - Claude 推理，跳过时为 {})
├── final_prd.json              (Stage 5 - Claude 推理)
├── final_prd_validation.json   (Stage 5 - validate_final_prd.py，含 attempt 字段)
├── semantic_gate_result.json   (Stage 6 - Claude 推理，跳过时为 skipped)
└── mission_result.json         (终态汇总)
```

---

## 四、状态持久化约定

### 重试计数（prd-compile attempt）

`final_prd_validation.json` 中记录 `attempt` 字段：

```json
{
  "status": "invalid",
  "attempt": 1,
  "can_auto_fix": true,
  "issues": [...]
}
```

每次重跑 Stage 5 前，读取该文件的 `attempt` 值，+1 后写回，再调用 prd-compile。
`attempt >= 3` 时不再重试，转为 blocked。

### Human-in-the-loop 恢复

暂停等待用户输入时，将暂停原因写入 `mission_result.json`：

```json
{
  "status": "blocked",
  "paused_at_stage": 4,
  "reason": "architect-converge needs_human_review",
  "human_review_reason": "...",
  "resume_instruction": "补充决策后执行：继续 Stage 5"
}
```

用户补充后，直接从 `paused_at_stage + 1` 继续，不重跑已完成的 stage。

---

## 五、raw_source.json Fallback 构造

MCP 未接入时，根据 input_ref.json 的 `input_kind` 手动构造 raw_source.json：

```json
{
  "source_type": "<input_kind>",
  "source_id": "<source_id>",
  "title": "",
  "description": "<用户原始输入完整文本>",
  "metadata": {},
  "comments": [],
  "attachments": []
}
```

将此文件写入 `artifacts/prd/<feature_id>/<version>/raw_source.json`，再继续执行 normalize_source.py。

---

## 六、终态输出

**ready**：
```json
{
  "status": "ready",
  "feature_id": "payment-callback-retry",
  "version": "v1",
  "previous_version": null,
  "final_prd_path": "artifacts/prd/payment-callback-retry/v1/final_prd.json",
  "stages_executed": ["intake", "context-build", "platform-review", "prd-compile"],
  "stages_skipped": ["architect-converge", "semantic-gate"]
}
```

**blocked**：
```json
{
  "status": "blocked",
  "paused_at_stage": 1,
  "missing_info": ["缺少目标用户定义", "缺少性能 SLA"],
  "resume_instruction": "补充以上信息后重新运行 prd-mission"
}
```

**skip_prd**：
```json
{
  "status": "skip_prd",
  "feature_id": "...",
  "reason": "task_type=skip_prd，无需生成 PRD"
}
```
