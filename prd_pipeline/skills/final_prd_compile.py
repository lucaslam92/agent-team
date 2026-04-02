"""
skill_final_prd_compile — Final PRD Compiler prompt (Gate 3).

Job: assemble the executable contract from all upstream decisions.
This is the only output that downstream engineering consumes.
Gate 3 validates the output before accepting it.
"""

import json
from prd_pipeline.models import (
    RequirementBrief, ContextBlock, ArchitectDecision,
    AggregatedPlatformReview,
)


SYSTEM = """\
You are the final PRD compiler in a product development pipeline.
You produce the single source of truth that engineering teams implement from.

You receive:
- The original requirement brief
- The architect's final decisions
- All platform constraints

You must produce a final_prd that is:
  COMPLETE — every feature has a full flow, expected behavior, and edge cases
  UNAMBIGUOUS — two engineers reading it must produce the same result
  IMPLEMENTABLE — no open questions, no "TBD", no "needs design"
  PLATFORM-ALIGNED — each feature's implementation notes address each platform

Rules:
1. Every feature must have: name, user_flow, expected_behavior, edge_cases, and implementation.
2. platform_alignment must have an entry for EVERY platform listed in the requirement.
3. Do not invent features not in the requirement or architect decision.
4. edge_cases must cover: error states, empty states, loading states, permission denied.
5. acceptance_criteria must be verifiable — a QA engineer must be able to write a test for each.
6. Respond with ONLY valid JSON.

Output schema:
{
  "features": [
    {
      "name": "feature name",
      "flow": {
        "user_flow": ["step 1", "step 2"],
        "expected_behavior": ["on action X, system does Y"],
        "edge_cases": ["if network fails, show error toast and allow retry"]
      },
      "implementation": {
        "approach": "one paragraph describing the implementation approach",
        "platform_alignment": {
          "android": "specific Android implementation note",
          "ios": "specific iOS implementation note",
          "web": "specific Web note",
          "backend": "specific Backend note"
        },
        "constraints": ["constraint the implementation must satisfy"]
      }
    }
  ],
  "acceptance_criteria": [
    "Given X, when Y, then Z"
  ]
}"""


def user_prompt(
    brief: RequirementBrief,
    architect_decision: ArchitectDecision,
    platform_reviews: AggregatedPlatformReview,
) -> str:
    all_constraints: list[str] = []
    for r in platform_reviews.platform_review_result:
        all_constraints.extend(
            f"[{r.platform.value}] {c}" for c in r.constraints
        )

    data = {
        "requirement_brief": {
            "feature_goal":        brief.feature_goal,
            "user_flow":           brief.user_flow,
            "acceptance_criteria": brief.acceptance_criteria,
            "platforms":           brief.platforms,
            "raw_notes":           brief.raw_notes,
        },
        "architect_decision": {
            "final_decisions":      architect_decision.final_decisions,
            "adjusted_features":    architect_decision.adjusted_features,
            "tradeoffs":            architect_decision.tradeoffs,
            "resolved_constraints": architect_decision.resolved_constraints,
        },
        "all_platform_constraints": all_constraints,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
