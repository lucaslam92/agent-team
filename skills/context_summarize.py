"""
context-summarize Skill

职责（v3 §9.2 / §8.3）：压缩 Feature / Rule / Capability，在 token 阈值内输出 context_summary

输入：
  --input   context_expanded.json 路径（含 feature_cards / rule_cards / capability_cards 等）
  --rules   effective_rules.json 路径（resolve_rules.py 的输出）
  --caps    effective_capabilities.json 路径（resolve_capabilities.py 的输出）
  --intake  intake_result.json 路径（用于传递 affected_platforms / task_type）
  --output  context_summary.json 路径

输出（v3 §8.2）：
  related_features       : list（最多 10 条）
  relevant_rules         : list（最多 20 条）
  available_capabilities : list（最多 15 条）
  platform_constraints   : list（最多 10 条）
  open_risks             : list（最多 8 条）
  playbook_cards         : list（透传，供 validate_final_prd.py 使用）
  affected_platforms     : list（透传自 intake_result）
  effective_rules        : list（透传自 effective_rules.json，供 validate_final_prd.py 使用）
"""

import argparse
import json
import os
from pathlib import Path

import anthropic

# v3 §8.3: token 阈值（条数上限）
LIMITS = {
    "related_features": 10,
    "relevant_rules": 20,
    "available_capabilities": 15,
    "platform_constraints": 10,
    "open_risks": 8,
}

SYSTEM_PROMPT = """你是一个技术文档压缩专家。你的任务是将输入的知识卡片（Feature / Rule / Capability）压缩为结构化摘要，用于后续 PRD 生成。

请分析输入内容，输出以下结构的 JSON（严格遵守条数上限）：

{
  "related_features": [
    {"id": "...", "name": "...", "summary": "不超过150字的摘要"}
    // 最多 10 条，按相关性降序
  ],
  "relevant_rules": [
    {"id": "...", "name": "...", "priority": "critical|high|normal", "summary": "不超过100字"}
    // 最多 20 条，priority=critical 的排在最前
  ],
  "available_capabilities": [
    {"id": "...", "name": "...", "summary": "不超过100字"}
    // 最多 15 条
  ],
  "platform_constraints": [
    {"platform": "...", "constraint": "约束描述"}
    // 最多 10 条，从 rule_cards 和 capability_cards 中识别平台限制
  ],
  "open_risks": [
    {"risk": "风险描述", "level": "blocker|high|medium|low", "source": "来源说明"}
    // 最多 8 条，blocker 级别必须排在最前
  ]
}

注意：
- 超出条数上限的内容按相关性分数截断
- open_risks 应识别跨端冲突、缺失能力、规则冲突等潜在风险
- 只输出 JSON，不要添加其他文字
"""


def build_input_text(expanded: dict, rules: dict, caps: dict, intake: dict) -> str:
    parts = []
    parts.append(f"## task_type: {intake.get('task_type', '')}")
    parts.append(f"## affected_platforms: {intake.get('affected_platforms', [])}")
    parts.append(f"## domains: {intake.get('domains', [])}")

    feature_cards = expanded.get("feature_cards", [])
    if feature_cards:
        parts.append("\n## Feature Cards（相关功能）")
        parts.append(json.dumps(feature_cards[:20], ensure_ascii=False))

    rule_cards = rules.get("effective_rules", expanded.get("rule_cards", []))
    if rule_cards:
        parts.append("\n## Rule Cards（有效规则）")
        parts.append(json.dumps(rule_cards[:30], ensure_ascii=False))

    cap_cards = caps.get("effective_capabilities", expanded.get("capability_cards", []))
    if cap_cards:
        parts.append("\n## Capability Cards（可用能力）")
        parts.append(json.dumps(cap_cards[:20], ensure_ascii=False))

    playbook_cards = expanded.get("playbook_cards", [])
    if playbook_cards:
        parts.append("\n## Playbook Cards（适用策略）")
        parts.append(json.dumps(playbook_cards, ensure_ascii=False))

    return "\n".join(parts)


def run_context_summarize(expanded: dict, rules: dict, caps: dict, intake: dict) -> dict:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    input_text = build_input_text(expanded, rules, caps, intake)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"请压缩以下知识内容：\n\n{input_text}",
            }
        ],
    )

    raw = message.content[0].text.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"模型返回内容中未找到 JSON：{raw[:200]}")

    result = json.loads(raw[start:end])

    # 强制截断至上限
    for key, limit in LIMITS.items():
        if key in result and isinstance(result[key], list):
            result[key] = result[key][:limit]

    # 透传字段（供下游使用）
    result["playbook_cards"] = expanded.get("playbook_cards", [])
    result["affected_platforms"] = intake.get("affected_platforms", [])
    result["effective_rules"] = rules.get("effective_rules", [])

    return result


def main():
    p = argparse.ArgumentParser(description="Context Summarize Skill")
    p.add_argument("--input", required=True, help="context_expanded.json 路径")
    p.add_argument("--rules", required=True, help="effective_rules.json 路径")
    p.add_argument("--caps", required=True, help="effective_capabilities.json 路径")
    p.add_argument("--intake", required=True, help="intake_result.json 路径")
    p.add_argument("--output", required=True, help="context_summary.json 输出路径")
    a = p.parse_args()

    expanded = json.loads(Path(a.input).read_text(encoding="utf-8"))
    rules = json.loads(Path(a.rules).read_text(encoding="utf-8"))
    caps = json.loads(Path(a.caps).read_text(encoding="utf-8"))
    intake = json.loads(Path(a.intake).read_text(encoding="utf-8"))

    result = run_context_summarize(expanded, rules, caps, intake)

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "open_risks": len(result.get("open_risks", []))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
