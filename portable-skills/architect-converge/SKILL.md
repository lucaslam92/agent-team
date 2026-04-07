---
name: architect-converge
description: >
  PRD Mission 流水线第四阶段（条件触发）：架构决策收敛。
  在 platform-review 发现跨端冲突或 blocker 风险后触发。
  以 Tech Lead + Architect 视角，对所有冲突和风险做出明确、可执行的架构决策，
  消除不确定性，输出 architect_decision.json。
---

# Architect Converge Skill

## 职责

对 platform-review 发现的冲突和风险做出架构层面的最终决策。
决策必须是**具体可执行的**，不能是模糊建议。
决策后如仍存在需业务方或跨团队确认的问题，标注 `needs_human_review=true`。

所有输入输出路径均基于 prd-mission 已解析好的 `run_dir = <artifact_root>/<feature_id>/<version>/`。

## 触发条件（满足任一则执行）

从 platform_review.json 中检查：
- `cross_platform_conflicts` 数量 > 0
- `blockers` 数量 > 0

从 `effective_rules.json` 中检查（注意：不是 context_summary.json）：
- `override_trace` 数组中存在 `priority=critical` 的规则被覆盖（即 `overridden_rule.priority == "critical"`）

> `override_trace` 字段由 resolve_rules.py 写入 `effective_rules.json`，记录每条覆盖关系。
> context_summary.json 中的 `effective_rules` 是压缩摘要，不含 override_trace，不能用于此判断。

**不满足时**：写入空对象 `{}` 到 architect_decision.json，跳过本 skill，直接进入 prd-compile。

---

## 分析输入

整合以下内容作为决策依据：

**来自 platform_review.json：**
- `per_platform_risks`：各端详细风险
- `cross_platform_conflicts`：跨端冲突列表
- `blockers`：blocker 级别风险

**来自 context_summary.json：**
- `relevant_rules`：有效规则（重点关注 priority=critical 的规则）
- `available_capabilities`：可用系统能力（用于评估解决方案可行性）

**来自 intake_result.json：**
- `task_type`、`summary`、`affected_platforms`、`domains`

---

## 决策原则

1. **每条决策必须可执行**：明确说明「做什么」和「怎么做」，而非「需要考虑」之类的模糊建议
2. **优先利用 available_capabilities**：如果已有系统能力可以解决问题，优先复用
3. **规则优先级**：repo > platform > global，决策不能违反高优先级规则
4. **Blocker 必须有对应决策**：每个 blocker 都需要一条决策来解除或转化它
5. **冲突收敛**：每个 cross_platform_conflict 都需要明确的解决方案

---

## needs_human_review 判断标准

以下情况需标注 `needs_human_review=true`：
- 决策涉及**核心业务变更**（如支付流程、权限体系、核心数据模型）
- 存在**技术上无法自动收敛的二选一**（两种方案各有取舍，需业务方决策）
- 存在**跨团队依赖**（需要其他团队的接口或资源，且目前不确定是否可用）

标注后，在 `human_review_reason` 中说明需要哪个角色（PM / 架构委员会 / 对应团队）确认什么问题。

---

## 输出格式

写入 `<artifact_root>/<feature_id>/<version>/architect_decision.json`：

```json
{
  "decisions": [
    {
      "decision_id": "d_001",
      "title": "决策标题（简短）",
      "description": "具体可执行的决策内容",
      "rationale": "决策理由（引用规则或能力）",
      "affects": ["backend", "ios"],
      "resolved_conflict_ids": ["c_001"],
      "resolved_blocker_ids": ["r_backend_001"]
    }
  ],
  "resolved_conflicts": [
    {
      "conflict_id": "c_001",
      "resolution": "解决方案描述",
      "decision_id": "d_001"
    }
  ],
  "needs_human_review": false,
  "human_review_reason": ""
}
```

---

## Human-in-the-Loop 处理

若 `needs_human_review=true`：
1. **立即停止**，不进入 prd-compile
2. 向用户展示 `human_review_reason` 和待决策的冲突/风险详情
3. 等待用户提供决策意见
4. 将用户决策补充到 architect_decision.json 的 `decisions` 中
5. 重新触发 prd-compile（此时 `needs_human_review` 应已变为 false）

---

## 下游流程

输出 architect_decision.json（且 `needs_human_review=false`）后，进入 **prd-compile** skill。
