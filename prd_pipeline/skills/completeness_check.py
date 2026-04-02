"""
skill_prd_completeness_check — Completeness Checker prompt (Gate 1).

Job: identify gaps that would BLOCK implementation. Not suggestions — blockers.
Output: completeness_report.
"""

import json
from prd_pipeline.models import RequirementBrief, ContextBlock


SYSTEM = """\
You are a completeness gate for a product development pipeline.
You decide whether the requirement is ready to proceed to design and engineering.

A requirement is BLOCKED if any of the following are true:
  - The feature_goal is ambiguous (two engineers would build different things)
  - A user_flow step has undefined behavior on a critical path
  - An acceptance criterion is untestable
  - A platform is listed but has no corresponding requirements
  - A constraint exists that makes the feature currently impossible

A requirement may CONTINUE even if:
  - Nice-to-have details are missing
  - Edge cases are not fully specified (that's for engineering)
  - Figma is not yet available

Rules:
1. missing_info: list only things that BLOCK progress. Not nice-to-haves.
2. assumptions: things you are assuming to be true that would unblock the requirement.
   These are explicit — the team must validate them.
3. risk_level: aggregate risk across all identified issues.
4. Be decisive — err toward CONTINUE if blockers are minor.
5. Respond with ONLY valid JSON.

Output schema:
{
  "status": "continue | blocked",
  "missing_info": ["specific missing item that blocks progress"],
  "assumptions": ["assumption being made to allow continuation"],
  "risk_level": "low | medium | high"
}"""


def user_prompt(brief: RequirementBrief, context: ContextBlock) -> str:
    data = {
        "requirement_brief": {
            "feature_goal":        brief.feature_goal,
            "user_flow":           brief.user_flow,
            "acceptance_criteria": brief.acceptance_criteria,
            "platforms":           brief.platforms,
            "raw_notes":           brief.raw_notes,
        },
        "context": {
            "related_modules":   context.related_modules,
            "existing_features": context.existing_features,
            "constraints":       context.constraints,
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
