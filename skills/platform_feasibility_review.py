"""
platform-feasibility-review Skill

职责（v3 §9.3）：多端可行性分析，输出风险与阻塞问题

内部执行策略（视角分治）：
  Phase 1：对 affected_platforms 中每个平台独立推理，输出各端风险列表
  Phase 2：在 Phase 1 基础上，做跨端冲突识别与优先级排序

触发条件（v3 §3.2）：
  - open_risks 数量 > 0
  - platform_constraints 数量 > 0
  - intake_result.task_type 为 new_feature 或 breaking_change
  - intake_result.affected_platforms 数量 > 1

输入：
  --context   context_summary.json 路径
  --intake    intake_result.json 路径
  --output    platform_review.json 路径

输出（v3 §9.3）：
  per_platform_risks      : dict[platform -> list[risk]]
  cross_platform_conflicts: list
  blockers                : list
  warnings                : list
"""

import argparse
import json
import os
from pathlib import Path

import anthropic

PHASE1_SYSTEM = """你是一个资深移动/后端平台架构师。你的任务是针对指定平台（{platform}）分析需求的可行性风险。

请输出以下 JSON 格式：
{{
  "platform": "{platform}",
  "risks": [
    {{
      "risk_id": "r_{platform}_001",
      "description": "风险描述",
      "level": "blocker|high|medium|low",
      "category": "technical|resource|dependency|compatibility|security|performance",
      "mitigation": "缓解建议（可选）"
    }}
  ]
}}

注意：
- 只分析 {platform} 平台，不考虑其他平台
- blocker 级别：实现不可行或会破坏现有功能
- high：有较大技术难度或依赖风险
- 只输出 JSON，不要其他文字
"""

PHASE2_SYSTEM = """你是一个跨端架构师。你已收到各端独立的风险分析结果，现在需要：

1. 识别跨端冲突（同一功能在不同平台实现不一致、接口不兼容等）
2. 识别 blocker 级别风险（汇总各端）
3. 识别 warning 级别风险（汇总各端）

请输出以下 JSON 格式：
{
  "cross_platform_conflicts": [
    {
      "conflict_id": "c_001",
      "platforms": ["backend", "ios"],
      "description": "冲突描述",
      "severity": "blocker|high|medium"
    }
  ],
  "blockers": [
    {
      "platform": "backend|ios|...",
      "risk_id": "r_backend_001",
      "description": "描述"
    }
  ],
  "warnings": [
    {
      "platform": "...",
      "risk_id": "...",
      "description": "描述"
    }
  ]
}

只输出 JSON，不要其他文字。
"""


def phase1_single_platform(client: anthropic.Anthropic, platform: str, context: dict, intake: dict) -> dict:
    """Phase 1: 针对单个平台独立分析"""
    input_text = f"""## 平台：{platform}
## task_type：{intake.get('task_type', '')}
## 需求摘要：{intake.get('summary', '')}
## 涉及域：{intake.get('domains', [])}

## 相关规则（该平台相关）：
{json.dumps([r for r in context.get('relevant_rules', []) if not r.get('platform') or r.get('platform') == platform], ensure_ascii=False)}

## 平台约束：
{json.dumps([c for c in context.get('platform_constraints', []) if c.get('platform') == platform or not c.get('platform')], ensure_ascii=False)}

## 可用能力：
{json.dumps(context.get('available_capabilities', []), ensure_ascii=False)}

## 已知风险（来自 context_summary）：
{json.dumps(context.get('open_risks', []), ensure_ascii=False)}
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=PHASE1_SYSTEM.format(platform=platform),
        messages=[{"role": "user", "content": f"请分析 {platform} 平台的可行性风险：\n\n{input_text}"}],
    )

    raw = message.content[0].text.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return {"platform": platform, "risks": []}
    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return {"platform": platform, "risks": []}


def phase2_cross_platform(client: anthropic.Anthropic, per_platform: dict) -> dict:
    """Phase 2: 跨端冲突识别与收敛"""
    input_text = f"## 各端风险分析结果：\n{json.dumps(per_platform, ensure_ascii=False, indent=2)}"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=PHASE2_SYSTEM,
        messages=[{"role": "user", "content": f"请识别跨端冲突并汇总 blocker/warning：\n\n{input_text}"}],
    )

    raw = message.content[0].text.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return {"cross_platform_conflicts": [], "blockers": [], "warnings": []}
    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return {"cross_platform_conflicts": [], "blockers": [], "warnings": []}


def run_platform_feasibility_review(context: dict, intake: dict) -> dict:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    platforms = intake.get("affected_platforms", [])
    if not platforms:
        return {
            "per_platform_risks": {},
            "cross_platform_conflicts": [],
            "blockers": [],
            "warnings": [],
            "_skipped": True,
            "_reason": "no affected_platforms",
        }

    # Phase 1: 各端独立分析
    per_platform_risks = {}
    for platform in platforms:
        result = phase1_single_platform(client, platform, context, intake)
        per_platform_risks[platform] = result.get("risks", [])

    # Phase 2: 跨端收敛
    phase2_result = phase2_cross_platform(client, per_platform_risks)

    return {
        "per_platform_risks": per_platform_risks,
        "cross_platform_conflicts": phase2_result.get("cross_platform_conflicts", []),
        "blockers": phase2_result.get("blockers", []),
        "warnings": phase2_result.get("warnings", []),
    }


def should_trigger(context: dict, intake: dict) -> bool:
    """v3 §3.2: 检查是否满足触发条件"""
    if len(context.get("open_risks", [])) > 0:
        return True
    if len(context.get("platform_constraints", [])) > 0:
        return True
    if intake.get("task_type") in ("new_feature", "breaking_change"):
        return True
    if len(intake.get("affected_platforms", [])) > 1:
        return True
    return False


def main():
    p = argparse.ArgumentParser(description="Platform Feasibility Review Skill")
    p.add_argument("--context", required=True, help="context_summary.json 路径")
    p.add_argument("--intake", required=True, help="intake_result.json 路径")
    p.add_argument("--output", required=True, help="platform_review.json 输出路径")
    p.add_argument("--force", action="store_true", help="强制执行，忽略触发条件检查")
    a = p.parse_args()

    context = json.loads(Path(a.context).read_text(encoding="utf-8"))
    intake = json.loads(Path(a.intake).read_text(encoding="utf-8"))

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not a.force and not should_trigger(context, intake):
        # 不满足触发条件，输出空对象（v3 §3.2）
        out.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "skipped", "reason": "trigger_conditions_not_met"}))
        return

    result = run_platform_feasibility_review(context, intake)

    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    blocker_count = len(result.get("blockers", []))
    conflict_count = len(result.get("cross_platform_conflicts", []))
    print(json.dumps({
        "status": "ok",
        "blocker_count": blocker_count,
        "conflict_count": conflict_count,
    }))


if __name__ == "__main__":
    main()
