---
name: semantic-gate
description: >
  PRD Mission 流水线最终阶段（可选触发）：语义一致性校验。
  在 prd-compile 输出 valid 的 final_prd.json 后，满足触发条件时执行。
  从语义层面检查 PRD 各章节之间是否存在逻辑矛盾，
  输出 semantic_gate_result.json（passed / failed）。
  与 validate_final_prd.py 的分工：后者做结构校验，本 skill 做语义推理校验。
---

# Semantic Gate Skill

## 职责

对 final_prd.json 进行语义一致性校验，确保文档各部分之间没有逻辑矛盾，
是结构性校验（validate_final_prd.py）之上的推理层补充。

## 触发条件（满足任一则执行）

从 intake_result.json 和 context_summary.json 中检查：
- `intake_result.task_type == "breaking_change"`
- `effective_rules` 中存在 `priority=critical` 的规则
- `final_prd` 涉及核心安全领域（文本中包含：payment / auth / permission / security / 支付 / 权限 / 安全 / 鉴权）

**不满足时**：写入 `{"status": "skipped", "reason": "trigger_conditions_not_met"}` 到 semantic_gate_result.json，流程继续输出终态。

---

## 六个校验维度

逐一检查以下维度，识别语义矛盾（而非字段缺失——那是 validate_final_prd.py 的职责）：

### 1. 目标一致性
PRD 的 `summary` 描述的目标，与 `features` 中的功能描述是否一致。
常见问题：summary 说「优化支付流程」，但 features 全是 UI 改动，无支付逻辑。

### 2. 方案可行性
`implementation_hint` 中的技术方向，是否与 `context_summary.available_capabilities` 匹配。
常见问题：hint 要求使用某个服务，但该服务 `availability=deprecated`。

### 3. 平台覆盖一致性
`affected_platforms` 列表，与 `platform_implementation` 的 key 集合是否对应。
常见问题：affected_platforms 包含 web，但 platform_implementation 只有 backend 和 ios。

### 4. 规则遵从性（语义层）
PRD 内容是否与 `priority=critical` 的规则存在**内容矛盾**（不是字段缺失）。
常见问题：规则要求「所有支付接口必须幂等」，但 implementation_hint 中描述的方案不支持幂等。

### 5. 验收标准完整性
`acceptance_criteria`（整体）是否覆盖了 `features` 中每个功能的核心验收点。
常见问题：features 中有 3 个功能，但 acceptance_criteria 只覆盖了 1 个。

### 6. 风险与缓解方案一致性
`risks_and_mitigations` 是否与 platform_review（blocker / warnings）中识别的风险对应。
常见问题：platform_review 发现了 2 个 blocker，但 PRD 中的 risks 只提到了 1 个，另一个被遗漏。

---

## 输出格式

写入 `artifacts/prd/<feature_id>/<version>/semantic_gate_result.json`：

```json
{
  "status": "passed | failed",
  "overall_consistency": "high | medium | low",
  "issues": [
    {
      "issue_id": "si_001",
      "dimension": "目标一致性 | 方案可行性 | 平台覆盖一致性 | 规则遵从性 | 验收标准完整性 | 风险一致性",
      "severity": "critical | high | medium | low",
      "description": "具体问题描述",
      "location": "PRD 中的具体位置（如 features[0].description）",
      "suggestion": "修复建议"
    }
  ],
  "recommendation": "总体评审意见（1-2句话）"
}
```

### status 判断规则（代码层确定性覆盖，不依赖推理结果）

完成分析后，按以下规则**强制覆盖** status，确保判断的确定性：

```
if any(issue.severity == "critical" for issue in issues)
  → status = "failed"
elif count(issue.severity == "high" for issue in issues) >= 2
  → status = "failed"
elif overall_consistency == "low"
  → status = "failed"
else
  → status = "passed"
```

---

## 结果处理

**`passed`（含 `skipped`）**：
- 写入 semantic_gate_result.json
- 继续输出终态 mission_result.json（`status: "ready"`）

**`failed`**：
- 展示 `issues` 列表给用户，说明哪些章节存在语义矛盾
- 决策权交给用户：
  - 若问题可在 PRD 层修复 → 将 `semantic_gate_result.json` 的路径作为上下文，重新触发 prd-compile。prd-compile 在步骤一生成 PRD 时，需读取该文件的 `issues` 字段作为 `semantic_errors` 修复指令（与 `validation_errors` 并列，但 attempt 计数独立重置为 0）
  - 若问题需要重新收集需求 → 回到 prd-intake，更新 `_revision`

> **接口约定**：semantic-gate 触发的 prd-compile 重跑，通过 `semantic_gate_result.json` 文件传递问题。prd-compile 每次执行前检查该文件是否存在，若存在且 `status=failed`，则在生成 PRD 时同时纳入 `semantic_errors` 修复指令。

---

## 与 validate_final_prd.py 的边界

| 维度 | validate_final_prd.py | semantic-gate skill |
|------|-----------------------|---------------------|
| 校验方式 | 确定性（代码逻辑） | 推理（Claude 判断） |
| 检查内容 | 字段存在 / 类型 / Playbook 章节覆盖 | 内容是否逻辑自洽 |
| 执行时机 | prd-compile 内部 | prd-compile 完成后 |
| 失败处理 | 自动重试（最多2次） | 人工介入 |
