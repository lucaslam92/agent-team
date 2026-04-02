"""
skill_platform_review — per-platform feasibility reviewer prompts.

One system prompt template + platform-specific context injected at call time.
Covers: Android, iOS, Web, Backend.
"""

import json
from prd_pipeline.models import RequirementBrief, ContextBlock


# ── Shared base ───────────────────────────────────────────────────────────────

_BASE_SYSTEM = """\
You are a {platform} platform reviewer for a product development pipeline.
Your job: assess whether this feature is feasible on {platform} given the requirement and context.

Evaluate:
1. Technical feasibility — can this be built with current {platform} tech stack?
2. Platform-specific constraints — OS limits, App Store rules, browser compatibility, API limits.
3. Integration points — what existing {platform} code/services does this touch?
4. Required changes — what must be added or modified?

Rules:
1. feasible = true only if the feature can be shipped without fundamental blockers.
2. issues: list problems that affect feasibility or quality. Be specific.
3. constraints: platform rules or technical limits the implementation must work within.
4. required_changes: what needs to be built or changed — not HOW, just WHAT.
5. risk_level: your overall assessment.
6. Respond with ONLY valid JSON.

Output schema:
{{
  "platform": "{platform_lower}",
  "feasible": true,
  "issues": ["specific issue"],
  "constraints": ["constraint"],
  "required_changes": ["change needed"],
  "risk_level": "low | medium | high"
}}"""


# ── Platform-specific context appended to user prompt ────────────────────────

_PLATFORM_CONTEXT = {
    "android": (
        "Consider: Android API levels, Jetpack Compose vs View system, "
        "background process restrictions, permissions, ProGuard/R8 implications."
    ),
    "ios": (
        "Consider: iOS version support, SwiftUI vs UIKit, App Store review policies, "
        "background execution limits, privacy manifests, entitlements."
    ),
    "web": (
        "Consider: browser compatibility (Chrome/Safari/Firefox), "
        "responsive breakpoints, CSP policies, bundle size, SSR/CSR tradeoffs."
    ),
    "backend": (
        "Consider: API contract changes (breaking vs non-breaking), "
        "database schema migrations, auth/authz, rate limits, data retention policies."
    ),
}


def system_prompt(platform: str) -> str:
    return _BASE_SYSTEM.format(
        platform=platform.capitalize(),
        platform_lower=platform.lower(),
    )


def user_prompt(
    platform: str,
    brief: RequirementBrief,
    context: ContextBlock,
) -> str:
    data = {
        "requirement_brief": {
            "feature_goal":        brief.feature_goal,
            "user_flow":           brief.user_flow,
            "acceptance_criteria": brief.acceptance_criteria,
            "platforms":           brief.platforms,
        },
        "context": {
            "related_modules":   context.related_modules,
            "existing_features": context.existing_features,
            "constraints":       context.constraints,
        },
    }
    p = platform.lower()
    extra = _PLATFORM_CONTEXT.get(p, "")
    return (
        f"{json.dumps(data, ensure_ascii=False, indent=2)}"
        + (f"\n\nPlatform context: {extra}" if extra else "")
    )
