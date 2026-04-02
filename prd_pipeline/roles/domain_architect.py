from __future__ import annotations
import json
from aadh.core.llm import LLMClient
from prd_pipeline.models import (
    RequirementBrief, PlatformReview, FigmaBundle, ArchitectDecision,
)
from prd_pipeline.skills import architect_converge


def run(
    client: LLMClient,
    brief: RequirementBrief,
    platform_reviews: list[PlatformReview],
    figma: FigmaBundle | None = None,
) -> ArchitectDecision:
    raw = client.chat(
        system=architect_converge.SYSTEM,
        user=architect_converge.user_prompt(brief, platform_reviews, figma),
        max_tokens=4096,
    )
    d = _parse(raw)
    return ArchitectDecision(
        final_decisions=d.get("final_decisions", []),
        adjusted_features=d.get("adjusted_features", []),
        tradeoffs=d.get("tradeoffs", []),
        resolved_constraints=d.get("resolved_constraints", []),
    )


def _parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)
