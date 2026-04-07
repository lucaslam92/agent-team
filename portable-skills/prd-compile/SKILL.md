---
name: prd-compile
description: >
  PRD Mission 流水线第五阶段：生成最终结构化 PRD，并执行三层校验。
  在 context-build（以及可选的 platform-review / architect-converge）完成后触发。
  输出 final_prd.json 和 final_prd_validation.json。
  校验失败时最多自动重试 2 次，仍失败则进入 human-in-the-loop 回路。
---

# PRD Compile Skill

## 职责

综合所有上游 artifacts，生成完整、结构化、可执行的 PRD（产品需求文档），
并通过 validate_final_prd.py 进行三层校验，保证 PRD 质量。

所有输入输出路径均基于 prd-mission 已解析好的 `run_dir = <artifact_root>/<feature_id>/<version>/`。

本 skill 分两步：
1. **推理层**（Claude 生成）：生成 final_prd.json
2. **脚本层**（确定性校验）：运行 `scripts/validate_final_prd.py` 做三层校验

---

## 输入文件

| 文件 | 必须 | 说明 |
|------|------|------|
| `context_summary.json` | ✅ | 相关功能 / 规则 / 能力 / 约束 / 风险 |
| `intake_result.json` | ✅ | task_type / platforms / summary / domains |
| `platform_review.json` | ❌ | 各端风险（如为 `{}` 则忽略） |
| `architect_decision.json` | ❌ | 架构决策（如为 `{}` 则忽略） |

---

## 步骤一：生成 final_prd.json（Claude 推理）

### PRD 必填结构

```json
{
  "title": "功能标题",
  "summary": "需求摘要（2-3句话）",
  "task_type": "...",
  "affected_platforms": ["backend", "ios"],
  "features": [
    {
      "feature_id": "f_001",
      "name": "功能名称",
      "description": "功能详细描述",
      "priority": "P0 | P1 | P2",
      "acceptance_criteria": ["验收标准1", "验收标准2"]
    }
  ],
  "acceptance_criteria": ["整体验收标准1", "..."],
  "implementation_hint": ["实现建议1（技术方向，非代码）", "..."],
  "platform_implementation": {
    "backend": {
      "approach": "实现方案描述",
      "key_components": ["组件1"],
      "dependencies": ["依赖1"]
    }
  },
  "flow": {
    "user_flow": ["步骤1：...", "步骤2：...", "步骤3：..."]
  },
  "risks_and_mitigations": [
    {
      "risk": "风险描述",
      "level": "blocker | high | medium | low",
      "mitigation": "缓解方案"
    }
  ],
  "open_questions": ["待确认问题1", "..."]
}
```

### 生成要点

**platform_implementation 覆盖原则**：`affected_platforms` 中的每个平台都必须有对应章节，即使某平台改动极小也要注明（如 "无前端改动，复用已有 UI"）

**Playbook 要求**：`context_summary.playbook_cards` 中每个 Playbook 的 `required_sections_in_prd` 必须在 PRD 中有对应字段

**Critical 规则体现**：`context_summary.effective_rules` 中 `priority=critical` 的规则，必须在 PRD 的相关章节中明确体现（在 implementation_hint、risks_and_mitigations 或专属章节中说明）

**架构决策融入**：若 architect_decision.json 非空，将 `decisions` 中每条决策的 `description` 体现到对应平台的 `platform_implementation.approach` 或 `implementation_hint` 中

**修复指令模式**：
- 若存在 `validation_errors`（validate 重试场景），针对每条 error 修复，不改动其他已正确章节
- 若 `semantic_gate_result.json` 存在且 `status=failed`（semantic-gate 回退场景），同时纳入其 `issues` 字段作为 `semantic_errors` 修复指令。两类错误分别处理，attempt 计数独立（semantic 回退时 attempt 重置为 0）

### 写入路径

```
<artifact_root>/<feature_id>/<version>/final_prd.json
```

---

## 步骤二：运行三层校验

```bash
python scripts/validate_final_prd.py \
  --input <artifact_root>/<feature_id>/<version>/final_prd.json \
  --context <artifact_root>/<feature_id>/<version>/context_summary.json \
  --output <artifact_root>/<feature_id>/<version>/final_prd_validation.json
```

### 三层校验内容

**Layer 1（Schema 合规性）**：必填字段存在且非空（features / flow.user_flow / acceptance_criteria / implementation_hint）

**Layer 2（完整性）**：
- Playbook `required_sections_in_prd` 字段全部存在
- `affected_platforms` 中每个平台都有 `platform_implementation` 章节

**Layer 3（规则合规性）**：
- `priority=critical` 的规则在 PRD 文本中有语义体现
- 无被 override 的低优先级规则错误出现

### 校验结果处理

读取 `final_prd_validation.json`，判断 `status` 字段：

**`valid`**：校验通过，继续进入 semantic-gate（条件触发）或直接输出终态

**`invalid` + `can_auto_fix=true`**（Layer 1 问题）：
- 读取 `final_prd_validation.json` 中的 `attempt` 字段（首次为 1）
- 若 `attempt < 3`：将 `issues` 作为修复指令，重新执行步骤一（生成 PRD），在 PRD 生成输入中附加 `validation_errors: <issues列表>`，生成后再次运行校验脚本，校验结果写回文件时 `attempt` +1
- 若 `attempt >= 3`：转为 blocked，等待人工介入

> **重要**：Claude 是无状态的，重试计数必须持久化到文件中。每次执行本 skill 前先读取 `final_prd_validation.json` 的 `attempt` 字段判断重试次数，不能依赖会话内存状态。

**`invalid` + `can_auto_fix=false`**（Layer 2/3 问题）：
- 立即停止，进入 human-in-the-loop 回路
- 向用户展示 `issues` 列表，说明 PRD 缺少哪些内容
- 等待用户补充信息后，重新从 prd-intake 或 context-build 阶段进入

---

## 输出终态（非 semantic-gate 场景）

所有校验通过后，写入 `mission_result.json`：

```json
{
  "status": "ready",
  "version": "<version>",
  "previous_version": "<prev_version>",
  "final_prd_path": "<artifact_root>/<feature_id>/<version>/final_prd.json",
  "diff_summary": "本次变更摘要（若有上一版本）"
}
```

---

## Artifacts 输出清单

| 文件 | 产出方 |
|------|--------|
| `final_prd.json` | Claude 推理 |
| `final_prd_validation.json` | validate_final_prd.py |
| `mission_result.json` | Claude（终态汇总） |
