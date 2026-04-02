"""
skill_architect_converge — Domain Architect prompt.

Job: eliminate all open questions and cross-platform conflicts.
Every tension between platforms must produce a single final decision.
Output: architect_decision.
"""

import json
from prd_pipeline.models import RequirementBrief, ContextBlock, PlatformReview, FigmaBundle


SYSTEM = """\
You are the domain architect in a product development pipeline.
You receive platform reviews and must converge all conflicts into final decisions.

Your job:
1. Identify every conflict between platform reviews (e.g. Android says X, iOS says Y).
2. Identify features that need adjustment due to platform constraints.
3. Make one clear final decision per conflict. No "it depends."
4. Document tradeoffs honestly — don't paper over real limitations.
5. Ensure every constraint from platform reviews is either resolved or escalated.

Rules:
1. final_decisions: one entry per resolved conflict or ambiguity. Each must be actionable.
2. adjusted_features: features that changed scope/behavior due to review findings.
3. tradeoffs: things the team is accepting suboptimal outcomes on, and why.
4. resolved_constraints: platform constraints that have been accounted for in decisions.
5. After your output, there must be NO remaining open_questions.
6. Respond with ONLY valid JSON.

Output schema:
{
  "final_decisions": [
    "Decision: <what was decided>. Rationale: <why>"
  ],
  "adjusted_features": [
    "Feature X: adjusted to Y because Z"
  ],
  "tradeoffs": [
    "Accepting: <suboptimal outcome> because <reason>"
  ],
  "resolved_constraints": [
    "Constraint: <constraint>. Resolution: <how it's handled>"
  ]
}"""


def user_prompt(
    brief: RequirementBrief,
    platform_reviews: list[PlatformReview],
    figma: FigmaBundle | None,
) -> str:
    reviews_data = [
        {
            "platform":         r.platform.value,
            "feasible":         r.feasible,
            "issues":           r.issues,
            "constraints":      r.constraints,
            "required_changes": r.required_changes,
            "risk_level":       r.risk_level.value,
        }
        for r in platform_reviews
    ]

    data: dict = {
        "requirement_brief": {
            "feature_goal":        brief.feature_goal,
            "user_flow":           brief.user_flow,
            "acceptance_criteria": brief.acceptance_criteria,
        },
        "platform_reviews": reviews_data,
    }

    if figma and (figma.layout or figma.interactions):
        figma_data: dict = {}
        if figma.layout:
            figma_data["screens"] = [
                {"name": s.name, "components": s.components}
                for s in figma.layout.screens
            ]
        if figma.interactions:
            figma_data["interactions"] = [
                {"trigger": i.trigger, "action": i.action, "target_screen": i.target_screen}
                for i in figma.interactions.interactions
            ]
        data["figma"] = figma_data

    return json.dumps(data, ensure_ascii=False, indent=2)
