---
name: platform-review
description: >
  PRD Mission 流水线第三阶段（条件触发）：多端可行性评审。
  在 context-build skill 完成后，满足触发条件时执行。
  采用「视角分治」策略：先各端独立分析，再跨端收敛，
  输出 platform_review.json（per_platform_risks / cross_platform_conflicts / blockers / warnings）。
---

# Platform Review Skill

## 职责

对当前需求进行多端可行性评审，识别各平台技术风险、跨端冲突和 blocker 级别问题。

所有输入输出路径均基于 prd-mission 已解析好的 `run_dir = <artifact_root>/<feature_id>/<version>/`。

## 触发条件（满足任一则执行）

从 context_summary.json 和 intake_result.json 中检查：
- `open_risks` 数量 > 0
- `platform_constraints` 数量 > 0
- `intake_result.task_type` 为 `new_feature` 或 `breaking_change`
- `affected_platforms` 数量 > 1

**不满足时**：写入空对象 `{}` 到 platform_review.json，跳过本 skill，直接进入 prd-compile。

---

## 执行策略：视角分治（两阶段）

单次多端并发推理容易导致各端相互干扰、推理质量下降。
因此采用两阶段策略：Phase 1 各端独立，Phase 2 跨端收敛。

---

## Phase 1：各端独立分析

对 `affected_platforms` 中的**每个平台**，独立进行可行性分析。
每次分析只关注该平台的视角，输入内容也只传入与该平台相关的规则和约束。

### 每个平台的分析输入

从 context_summary.json 中过滤，只传入与当前平台相关的内容：
- `relevant_rules`：过滤 `scope.platform == <platform>` 或 scope=global 的规则
  - **注意**：规则的平台字段在 `scope.platform`，不是顶层 `platform`
- `platform_constraints`：过滤 `platform == <platform>` 或无 platform 字段的约束
- `available_capabilities`：全量传入（能力通常是跨平台的）
- `open_risks`：全量传入（作为已知风险背景）

额外传入：
- `intake_result.summary`：需求摘要
- `intake_result.task_type`：需求类型
- `intake_result.domains`：业务领域

### 每个平台的分析输出

```json
{
  "platform": "backend",
  "risks": [
    {
      "risk_id": "r_backend_001",
      "description": "风险描述",
      "level": "blocker | high | medium | low",
      "category": "technical | resource | dependency | compatibility | security | performance",
      "mitigation": "缓解建议（可选）"
    }
  ]
}
```

风险级别定义：
- `blocker`：实现不可行，或会破坏现有功能，必须解决才能继续
- `high`：有较大技术难度或依赖风险，需在 PRD 中明确方案
- `medium` / `low`：已知但可接受的风险，记录即可

---

## Phase 2：跨端冲突收敛

将 Phase 1 所有平台的风险列表汇总，识别：

**跨端冲突**：同一功能在不同平台实现存在不一致（如接口定义不兼容、数据格式不同、时序不一致）

**Blocker 汇总**：从所有平台风险中提取 `level=blocker` 的条目

**Warning 汇总**：从所有平台风险中提取 `level=high` 的条目

### Phase 2 分析要点

- 跨端冲突通常出现在：API 契约、数据模型、状态机定义、权限模型等维度
- 若两个平台对同一功能的实现方案存在前置假设矛盾，即为冲突
- 优先级：blocker 冲突 > blocker 风险 > high 冲突 > high 风险

---

## 输出格式

写入 `<artifact_root>/<feature_id>/<version>/platform_review.json`：

```json
{
  "per_platform_risks": {
    "backend": [
      {
        "risk_id": "r_backend_001",
        "description": "...",
        "level": "high",
        "category": "dependency",
        "mitigation": "..."
      }
    ],
    "ios": [...]
  },
  "cross_platform_conflicts": [
    {
      "conflict_id": "c_001",
      "platforms": ["backend", "ios"],
      "description": "冲突描述",
      "severity": "blocker | high | medium"
    }
  ],
  "blockers": [
    {
      "platform": "backend",
      "risk_id": "r_backend_001",
      "description": "描述"
    }
  ],
  "warnings": [
    {
      "platform": "ios",
      "risk_id": "r_ios_002",
      "description": "描述"
    }
  ]
}
```

---

## 下游流程决策

输出 platform_review.json 后，检查是否需要触发 architect-converge skill：

**触发 architect-converge 的条件**（满足任一）：
- `cross_platform_conflicts` 数量 > 0
- `blockers` 数量 > 0
- `effective_rules` 中存在互相冲突的规则（通过 override_trace 判断是否有被覆盖的 critical 规则）

不满足则跳过 architect-converge，直接进入 **prd-compile** skill。
