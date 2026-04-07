"""
final-prd-compile Skill

职责（v3 §9.5）：输出最终结构化 PRD

输入：
  --context           context_summary.json 路径
  --platform-review   platform_review.json 路径（可为空对象 {}）
  --architect         architect_decision.json 路径（可为空对象 {}）
  --intake            intake_result.json 路径
  --validation-errors 可选，上一轮校验失败的 validation_errors（JSON 字符串），用于自动修复重试
  --output            final_prd.json 路径

输出（结构化 PRD，v3 §10.1 Layer1 必填字段）：
  title                  : str
  summary                : str
  task_type              : str
  affected_platforms     : list
  features               : list[feature]
  acceptance_criteria    : list[str]
  implementation_hint    : list[str]
  platform_implementation: dict[platform -> impl]
  flow                   : { user_flow: list[str] }
  risks_and_mitigations  : list
  open_questions         : list
  （Playbook required_sections 动态添加）
"""

import argparse
import json
import os
from pathlib import Path

import anthropic

SYSTEM_PROMPT = """你是一个专业的产品经理（PM）和技术文档撰写专家。你的任务是根据需求分析、上下文摘要、可行性评审和架构决策，输出一份完整的结构化 PRD（产品需求文档）。

PRD 必须包含以下字段（JSON 格式）：

{
  "title": "功能标题",
  "summary": "需求摘要（2-3句话）",
  "task_type": "new_feature|enhancement|bug_fix|breaking_change|config_change",
  "affected_platforms": ["backend", "ios", ...],
  "features": [
    {
      "feature_id": "f_001",
      "name": "功能名称",
      "description": "功能详细描述",
      "priority": "P0|P1|P2",
      "acceptance_criteria": ["验收标准1", "验收标准2"]
    }
  ],
  "acceptance_criteria": ["整体验收标准1", "..."],
  "implementation_hint": [
    "实现建议1（技术方向，非代码）",
    "实现建议2"
  ],
  "platform_implementation": {
    "backend": {
      "approach": "实现方案描述",
      "key_components": ["组件1", "组件2"],
      "dependencies": ["依赖1"]
    }
  },
  "flow": {
    "user_flow": [
      "步骤1：用户触发...",
      "步骤2：系统响应...",
      "步骤3：..."
    ]
  },
  "risks_and_mitigations": [
    {
      "risk": "风险描述",
      "level": "blocker|high|medium|low",
      "mitigation": "缓解方案"
    }
  ],
  "open_questions": [
    "待确认问题1",
    "待确认问题2"
  ]
}

注意：
- platform_implementation 必须覆盖 affected_platforms 中的每一个平台
- Playbook 要求的 required_sections_in_prd 中的字段必须包含在 PRD 中
- critical 级别规则必须在 PRD 中有明确体现
- 如果有 validation_errors（修复指令），必须针对性修复每一项
- 只输出 JSON，不要其他文字
"""


def build_compile_input(context: dict, platform_review: dict, architect: dict, intake: dict,
                         validation_errors: list) -> str:
    parts = []
    parts.append(f"## 需求基本信息")
    parts.append(f"- task_type: {intake.get('task_type', '')}")
    parts.append(f"- summary: {intake.get('summary', '')}")
    parts.append(f"- affected_platforms: {intake.get('affected_platforms', [])}")
    parts.append(f"- domains: {intake.get('domains', [])}")

    parts.append("\n## 相关功能（related_features）")
    parts.append(json.dumps(context.get("related_features", []), ensure_ascii=False))

    parts.append("\n## 有效规则（relevant_rules）")
    parts.append(json.dumps(context.get("relevant_rules", []), ensure_ascii=False))

    parts.append("\n## 可用能力（available_capabilities）")
    parts.append(json.dumps(context.get("available_capabilities", []), ensure_ascii=False))

    parts.append("\n## 平台约束（platform_constraints）")
    parts.append(json.dumps(context.get("platform_constraints", []), ensure_ascii=False))

    parts.append("\n## 已知风险（open_risks）")
    parts.append(json.dumps(context.get("open_risks", []), ensure_ascii=False))

    if platform_review and platform_review != {}:
        parts.append("\n## 平台可行性评审（platform_review）")
        parts.append(json.dumps(platform_review, ensure_ascii=False))

    if architect and architect != {}:
        parts.append("\n## 架构决策（architect_decision）")
        parts.append(json.dumps(architect, ensure_ascii=False))

    playbook_cards = context.get("playbook_cards", [])
    if playbook_cards:
        parts.append("\n## 适用 Playbook（required_sections 必须在 PRD 中体现）")
        parts.append(json.dumps(playbook_cards, ensure_ascii=False))

    if validation_errors:
        parts.append("\n## 【修复指令】上一轮校验失败，请针对以下问题修复 PRD：")
        parts.append(json.dumps(validation_errors, ensure_ascii=False))

    return "\n".join(parts)


def run_final_prd_compile(context: dict, platform_review: dict, architect: dict, intake: dict,
                           validation_errors: list) -> dict:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    input_text = build_compile_input(context, platform_review, architect, intake, validation_errors)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"请生成结构化 PRD：\n\n{input_text}"}],
    )

    raw = message.content[0].text.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"模型返回内容中未找到 JSON：{raw[:200]}")

    result = json.loads(raw[start:end])

    # 补齐 Layer 1 必填字段（防御性处理）
    result.setdefault("title", intake.get("summary", "未命名需求"))
    result.setdefault("summary", "")
    result.setdefault("task_type", intake.get("task_type", ""))
    result.setdefault("affected_platforms", intake.get("affected_platforms", []))
    result.setdefault("features", [])
    result.setdefault("acceptance_criteria", [])
    result.setdefault("implementation_hint", [])
    result.setdefault("platform_implementation", {})
    result.setdefault("flow", {"user_flow": []})
    result.setdefault("risks_and_mitigations", [])
    result.setdefault("open_questions", [])

    return result


def main():
    p = argparse.ArgumentParser(description="Final PRD Compile Skill")
    p.add_argument("--context", required=True, help="context_summary.json 路径")
    p.add_argument("--platform-review", required=True, help="platform_review.json 路径")
    p.add_argument("--architect", required=True, help="architect_decision.json 路径")
    p.add_argument("--intake", required=True, help="intake_result.json 路径")
    p.add_argument("--validation-errors", default=None,
                   help="上一轮 validation_errors（JSON 字符串），用于修复重试")
    p.add_argument("--output", required=True, help="final_prd.json 输出路径")
    a = p.parse_args()

    context = json.loads(Path(a.context).read_text(encoding="utf-8"))
    platform_review = json.loads(Path(a.platform_review).read_text(encoding="utf-8"))
    architect = json.loads(Path(a.architect).read_text(encoding="utf-8"))
    intake = json.loads(Path(a.intake).read_text(encoding="utf-8"))
    validation_errors = json.loads(a.validation_errors) if a.validation_errors else []

    result = run_final_prd_compile(context, platform_review, architect, intake, validation_errors)

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": "ok",
        "feature_count": len(result.get("features", [])),
        "platform_count": len(result.get("platform_implementation", {})),
    }))


if __name__ == "__main__":
    main()
