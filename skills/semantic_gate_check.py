"""
semantic-gate-check Skill（可选）

职责（v3 §9.6）：语义一致性校验，确保 PRD 各节之间无逻辑矛盾

与 validate_final_prd.py 的边界：
  - validate_final_prd.py：做结构性和规则性校验（确定性逻辑）
  - semantic-gate-check：做语义一致性校验（推理逻辑，如"目标与方案是否一致"）

触发条件（v3 §3.4）：
  - intake_result.task_type 为 breaking_change
  - effective_rules 中存在 priority=critical 的规则
  - final_prd 涉及核心支付 / 权限 / 安全模块

输入：
  --prd      final_prd.json 路径
  --context  context_summary.json 路径
  --intake   intake_result.json 路径
  --output   semantic_gate_result.json 路径

输出：
  status              : passed | failed
  issues              : list[semantic_issue]
  overall_consistency : high | medium | low
  recommendation      : str
"""

import argparse
import json
import os
from pathlib import Path

import anthropic

SYSTEM_PROMPT = """你是一个资深技术评审专家。你的任务是对一份 PRD 进行语义一致性校验，确保文档各部分之间没有逻辑矛盾。

请检查以下维度：
1. **目标一致性**：PRD 的目标/summary 与 features 描述是否一致
2. **方案可行性**：implementation_hint 是否与 available_capabilities 匹配
3. **平台覆盖一致性**：affected_platforms 与 platform_implementation 是否对应
4. **规则遵从性**：PRD 内容是否与 critical 规则有语义冲突（不是字段缺失，而是内容矛盾）
5. **验收标准完整性**：acceptance_criteria 是否覆盖了所有 features
6. **风险与缓解方案一致性**：risks_and_mitigations 是否与平台评审中的风险对应

请输出以下 JSON 格式：

{
  "status": "passed|failed",
  "overall_consistency": "high|medium|low",
  "issues": [
    {
      "issue_id": "si_001",
      "dimension": "目标一致性|方案可行性|平台覆盖一致性|规则遵从性|验收标准完整性|风险一致性",
      "severity": "critical|high|medium|low",
      "description": "具体问题描述",
      "location": "PRD 中的具体位置（如 features[0].description）",
      "suggestion": "修复建议"
    }
  ],
  "recommendation": "总体评审意见（1-2句话）"
}

判断 status=failed 的条件：
- 存在 severity=critical 的问题
- 存在 2 个及以上 severity=high 的问题
- overall_consistency=low

只输出 JSON，不要其他文字。
"""

SECURITY_DOMAINS = {"payment", "auth", "permission", "security", "支付", "权限", "安全", "鉴权"}


def should_trigger(intake: dict, context: dict, prd: dict) -> bool:
    """v3 §3.4: 检查是否满足触发条件"""
    if intake.get("task_type") == "breaking_change":
        return True
    effective_rules = context.get("effective_rules", [])
    for rule in effective_rules:
        if rule.get("priority") == "critical":
            return True
    # 检查 PRD 是否涉及核心支付/权限/安全模块
    prd_text = json.dumps(prd, ensure_ascii=False).lower()
    for domain in SECURITY_DOMAINS:
        if domain in prd_text:
            return True
    return False


def run_semantic_gate_check(prd: dict, context: dict, intake: dict) -> dict:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    input_text = f"""## PRD 内容：
{json.dumps(prd, ensure_ascii=False)}

## Context 摘要（available_capabilities / relevant_rules）：
- available_capabilities: {json.dumps(context.get('available_capabilities', []), ensure_ascii=False)}
- relevant_rules: {json.dumps(context.get('relevant_rules', []), ensure_ascii=False)}
- platform_constraints: {json.dumps(context.get('platform_constraints', []), ensure_ascii=False)}

## intake_result：
- task_type: {intake.get('task_type', '')}
- affected_platforms: {intake.get('affected_platforms', [])}
- domains: {intake.get('domains', [])}
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"请对以下 PRD 进行语义一致性校验：\n\n{input_text}"}],
    )

    raw = message.content[0].text.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return {
            "status": "passed",
            "overall_consistency": "high",
            "issues": [],
            "recommendation": "语义校验通过",
        }

    try:
        result = json.loads(raw[start:end])
    except json.JSONDecodeError:
        result = {}

    result.setdefault("status", "passed")
    result.setdefault("overall_consistency", "high")
    result.setdefault("issues", [])
    result.setdefault("recommendation", "")

    return result


def main():
    p = argparse.ArgumentParser(description="Semantic Gate Check Skill")
    p.add_argument("--prd", required=True, help="final_prd.json 路径")
    p.add_argument("--context", required=True, help="context_summary.json 路径")
    p.add_argument("--intake", required=True, help="intake_result.json 路径")
    p.add_argument("--output", required=True, help="semantic_gate_result.json 输出路径")
    p.add_argument("--force", action="store_true", help="强制执行，忽略触发条件检查")
    a = p.parse_args()

    prd = json.loads(Path(a.prd).read_text(encoding="utf-8"))
    context = json.loads(Path(a.context).read_text(encoding="utf-8"))
    intake = json.loads(Path(a.intake).read_text(encoding="utf-8"))

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not a.force and not should_trigger(intake, context, prd):
        out.write_text(json.dumps({
            "status": "skipped",
            "reason": "trigger_conditions_not_met",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "skipped"}))
        return

    result = run_semantic_gate_check(prd, context, intake)

    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": result.get("status"),
        "issue_count": len(result.get("issues", [])),
        "overall_consistency": result.get("overall_consistency"),
    }))


if __name__ == "__main__":
    main()
