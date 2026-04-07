---
name: prd-intake
description: >
  PRD Mission 流水线的第一阶段：输入解析 + 需求 intake 检查。
  当用户提供一个需求输入（Jira key、Google Doc URL、Confluence URL 或原始文本），
  需要进入 PRD 自动化生成流程时，使用此 skill。
  完成后输出 input_ref.json、normalized_input.json、resource_index.json、intake_result.json。
---

# PRD Intake Skill

## 职责

将原始用户输入转化为结构化的 intake 结果，决定后续流程走向（proceed / blocked / skip_prd）。

本 skill 分两步：
1. **脚本层**（确定性处理）：运行 `scripts/` 中的三个脚本，解析并标准化输入
2. **推理层**（Claude 判断）：基于 normalized_input 做 task 分类、completeness 检查，输出 intake_result.json

---

## 步骤一：运行输入解析脚本

skill 目录下的 `scripts/` 包含三个脚本，按顺序执行：

### 1.1 resolve_input.py
解析用户原始输入，识别输入类型（jira / gdoc / gsheet / confluence / raw_text）。

```bash
python scripts/resolve_input.py \
  --input "<用户原始输入字符串>" \
  --output artifacts/prd/<feature_id>/v<N>/input_ref.json \
  --revision <N>   # 首次为 0，human-in-the-loop 补充时递增
```

### 1.2 normalize_source.py
将 MCP 获取的 raw_source.json 标准化，提取 title、normalized_text、signals、linked_resources。

> **注意**：raw_source.json 由 MCP 工具（Jira / GDoc / Confluence MCP）fetch 后提供。
> 若 MCP 尚未接入，直接将用户输入作为 raw_source 的 `source_ref` 字段传入。
> human-in-the-loop 补充轮次时，传入 `--base` 参数指向上一轮 normalized_input.json。

```bash
python scripts/normalize_source.py \
  --input artifacts/prd/<feature_id>/v<N>/raw_source.json \
  --output artifacts/prd/<feature_id>/v<N>/normalized_input.json \
  [--base artifacts/prd/<feature_id>/v<N-1>/normalized_input.json]  # 仅补充轮次使用
```

### 1.3 resolve_resources.py
构建 resource_index.json，尝试 fetch linked_resources 中的外部资源（Figma / GDoc / GSheet）。

> **注意**：此脚本目前为 stub，MCP fetch 尚未实现。
> 未实现的资源会标记为 `pending_mcp`，不阻塞后续流程。

```bash
python scripts/resolve_resources.py \
  --input artifacts/prd/<feature_id>/v<N>/normalized_input.json \
  --resources-dir artifacts/prd/<feature_id>/v<N>/resources/ \
  --output artifacts/prd/<feature_id>/v<N>/resource_index.json
```

---

## 步骤二：执行 Intake 推理

读取 `normalized_input.json`，对需求进行分析，输出 `intake_result.json`。

### 分析维度

**task_type 分类**（从以下类型中选一个）：
- `new_feature`：全新功能
- `enhancement`：已有功能的增强
- `bug_fix`：缺陷修复
- `breaking_change`：会破坏已有接口 / 行为的变更
- `config_change`：纯配置 / 文案 / 样式等低风险变更
- `skip_prd`：无需撰写 PRD 的微小改动（如错别字修正、颜色微调）

**affected_platforms 识别**：从以下范围选择实际受影响的平台：
`android`, `ios`, `web`, `backend`, `cross`（跨端）

**completeness 判断**：
- `complete`：需求描述完整，包含目标、范围、关键约束，可进入 PRD 生成
- `incomplete`：关键信息缺失，无法撰写 PRD

**missing_info 提取**：若 completeness=incomplete，列出具体缺失项（用户需补充的内容）

**status 决策**：
- `proceed`：信息完整，可继续
- `blocked`：信息不完整，等待用户补充
- `skip_prd`：无需生成 PRD（task_type=skip_prd 时强制设为此值）

**domains 识别**：从 normalized_text 中识别业务领域（如 payment、order、auth、notification 等）

### 输入分析要点

只需关注 normalized_input.json 中以下字段，忽略 linked_resources、attachments 等：
- `title`
- `normalized_text`
- `signals`（already extracted: mentions_backend, mentions_ui, mentions_multi_platform 等）
- `metadata.issue_type`, `metadata.labels`, `metadata.priority`

### 输出格式

将结果写入 `artifacts/prd/<feature_id>/v<N>/intake_result.json`：

```json
{
  "task_type": "new_feature",
  "affected_platforms": ["backend", "ios"],
  "completeness": "complete",
  "missing_info": [],
  "status": "proceed",
  "summary": "一句话需求摘要（不超过100字）",
  "domains": ["payment"],
  "signals": {
    "mentions_backend": true,
    "mentions_ui": false,
    "mentions_state_flow": false
  }
}
```

---

## 早退出规则

输出 intake_result.json 后，检查 status：

- **`blocked`**：立即停止，告知用户 `missing_info` 列表，等待补充。补充后重新运行本 skill，传入 `--revision N+1` 和 `--base` 参数。
- **`skip_prd`**：立即停止，输出 `mission_result.json` 为 `{"status": "skip_prd", "reason": "..."}`，整个流程结束。
- **`proceed`**：继续，将 intake_result.json 传递给 **context-build** skill。

---

## Artifacts 输出清单

| 文件 | 产出方 |
|------|--------|
| `input_ref.json` | resolve_input.py |
| `raw_source.json` | MCP（或用户提供） |
| `normalized_input.json` | normalize_source.py |
| `resource_index.json` | resolve_resources.py |
| `intake_result.json` | Claude 推理 |
