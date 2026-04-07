"""
architect-converge Skill

职责（v3 §9.4）：收敛冲突 / 输出最终决策 / 消灭不确定性

触发条件（v3 §3.3）：
  - 存在跨端冲突（cross_platform_conflicts 数量 > 0）
  - 存在 blocker 级别风险（risk_level = blocker）
  - 存在多个 effective_rules 互相冲突

输入：
  --platform-review  platform_review.json 路径
  --context          context_summary.json 路径
  --intake           intake_result.json 路径
  --output           architect_decision.json 路径

输出（v3 §9.4）：
  decisions           : list[decision]
  resolved_conflicts  : list
  needs_human_review  : bool
  human_review_reason : str
"""

import argparse
import json
import os
from pathlib import Path

import anthropic

SYSTEM_PROMPT = """你是一个资深系统架构师（Tech Lead + Architect）。你的任务是根据多端可行性评审结果，做出明确的架构决策，消除不确定性和冲突。

请分析输入内容，输出以下 JSON 格式：

{
  "decisions": [
    {
      "decision_id": "d_001",
      "title": "决策标题",
      "description": "决策内容（具体、可执行）",
      "rationale": "决策理由",
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

判断 needs_human_review=true 的条件：
- 存在架构决策涉及重大业务风险（如支付流程变更、权限体系重构）
- 存在技术上无法自动收敛的冲突（如两种方案各有取舍，需要业务方决策）
- 存在跨团队依赖需要协商的情况

注意：
- decisions 中每一条必须是具体可执行的（不是模糊建议）
- 如果没有需要解决的冲突，decisions 可以为空数组
- 只输出 JSON，不要其他文字
"""


def should_trigger(platform_review: dict, context: dict) -> bool:
    """v3 §3.3: 检查是否满足触发条件"""
    if len(platform_review.get("cross_platform_conflicts", [])) > 0:
        return True
    if len(platform_review.get("blockers", [])) > 0:
        return True
    # 检查 effective_rules 中是否存在冲突（通过 conflicts_with 边类型）
    effective_rules = context.get("effective_rules", [])
    for rule in effective_rules:
        if rule.get("conflicts_with"):
            return True
    return False


def run_architect_converge(platform_review: dict, context: dict, intake: dict) -> dict:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    input_text = f"""## task_type：{intake.get('task_type', '')}
## 需求摘要：{intake.get('summary', '')}
## affected_platforms：{intake.get('affected_platforms', [])}

## 各端风险（per_platform_risks）：
{json.dumps(platform_review.get('per_platform_risks', {}), ensure_ascii=False)}

## 跨端冲突（cross_platform_conflicts）：
{json.dumps(platform_review.get('cross_platform_conflicts', []), ensure_ascii=False)}

## Blocker 风险：
{json.dumps(platform_review.get('blockers', []), ensure_ascii=False)}

## 有效规则（relevant_rules）：
{json.dumps(context.get('relevant_rules', []), ensure_ascii=False)}

## 可用能力（available_capabilities）：
{json.dumps(context.get('available_capabilities', []), ensure_ascii=False)}
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"请做出架构决策，收敛以下冲突和风险：\n\n{input_text}"}],
    )

    raw = message.content[0].text.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return {
            "decisions": [],
            "resolved_conflicts": [],
            "needs_human_review": False,
            "human_review_reason": "",
        }

    try:
        result = json.loads(raw[start:end])
    except json.JSONDecodeError:
        result = {}

    result.setdefault("decisions", [])
    result.setdefault("resolved_conflicts", [])
    result.setdefault("needs_human_review", False)
    result.setdefault("human_review_reason", "")

    return result


def main():
    p = argparse.ArgumentParser(description="Architect Converge Skill")
    p.add_argument("--platform-review", required=True, help="platform_review.json 路径")
    p.add_argument("--context", required=True, help="context_summary.json 路径")
    p.add_argument("--intake", required=True, help="intake_result.json 路径")
    p.add_argument("--output", required=True, help="architect_decision.json 输出路径")
    p.add_argument("--force", action="store_true", help="强制执行，忽略触发条件检查")
    a = p.parse_args()

    platform_review = json.loads(Path(a.platform_review).read_text(encoding="utf-8"))
    context = json.loads(Path(a.context).read_text(encoding="utf-8"))
    intake = json.loads(Path(a.intake).read_text(encoding="utf-8"))

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not a.force and not should_trigger(platform_review, context):
        # 不满足触发条件，输出空对象（v3 §3.3）
        out.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "skipped", "reason": "trigger_conditions_not_met"}))
        return

    result = run_architect_converge(platform_review, context, intake)

    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": "ok",
        "decision_count": len(result.get("decisions", [])),
        "needs_human_review": result.get("needs_human_review", False),
    }))


if __name__ == "__main__":
    main()
