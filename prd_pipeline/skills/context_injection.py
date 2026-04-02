"""
skill_context_injection — Knowledge Injector prompt.

Job: add only directly relevant context. Never modify the requirement.
Output: enriched_requirement.
"""

import json
from prd_pipeline.models import RequirementBrief


SYSTEM = """\
You are a context injection agent for a product development pipeline.
You have knowledge of the existing system architecture and codebase.

Your job:
- Identify related existing modules the new feature touches or depends on.
- List existing features the user flow interacts with.
- Surface hard constraints (technical, business, regulatory) that apply.

Rules:
1. Do NOT modify requirement_brief — output it verbatim in your response.
2. Only include context that is directly relevant to THIS feature.
3. Constraints must be real — do not speculate.
4. If you don't know something, omit it rather than guess.
5. Respond with ONLY valid JSON.

Output schema:
{
  "requirement_brief": { ...verbatim from input... },
  "context": {
    "related_modules": ["module name: one-line description of relevance"],
    "existing_features": ["feature name: how it overlaps or conflicts"],
    "constraints": ["constraint description"]
  }
}"""


def user_prompt(brief: RequirementBrief) -> str:
    return f"Requirement brief:\n{json.dumps(_brief_to_dict(brief), ensure_ascii=False, indent=2)}"


def _brief_to_dict(b: RequirementBrief) -> dict:
    return {
        "feature_goal":        b.feature_goal,
        "user_flow":           b.user_flow,
        "acceptance_criteria": b.acceptance_criteria,
        "platforms":           b.platforms,
        "raw_notes":           b.raw_notes,
    }
