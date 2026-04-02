"""
Platform Reviewer — one function handles all four platforms.
Runs in parallel via concurrent.futures if multiple platforms are needed.
"""
from __future__ import annotations
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from aadh.core.llm import LLMClient
from prd_pipeline.models import (
    RequirementBrief, ContextBlock, Platform, PlatformReview,
    AggregatedPlatformReview, RiskLevel,
)
from prd_pipeline.skills import platform_review as skill


def run_one(
    client: LLMClient,
    platform: Platform,
    brief: RequirementBrief,
    context: ContextBlock,
) -> PlatformReview:
    raw = client.chat(
        system=skill.system_prompt(platform.value),
        user=skill.user_prompt(platform.value, brief, context),
    )
    d = _parse(raw)
    return PlatformReview(
        platform=platform,
        feasible=bool(d.get("feasible", False)),
        issues=d.get("issues", []),
        constraints=d.get("constraints", []),
        required_changes=d.get("required_changes", []),
        risk_level=RiskLevel(d.get("risk_level", "high")),
    )


def run_all(
    make_client,           # callable(platform_name) -> LLMClient
    platforms: list[str],
    brief: RequirementBrief,
    context: ContextBlock,
) -> AggregatedPlatformReview:
    """
    Run all requested platform reviews in parallel.
    make_client allows each platform to use a different model if needed.
    """
    requested = [Platform(p) for p in platforms if p in Platform._value2member_map_]

    reviews: list[PlatformReview] = []
    with ThreadPoolExecutor(max_workers=len(requested) or 1) as pool:
        futures = {
            pool.submit(run_one, make_client(p.value), p, brief, context): p
            for p in requested
        }
        for future in as_completed(futures):
            reviews.append(future.result())

    blocking = [
        f"[{r.platform.value}] {issue}"
        for r in reviews
        for issue in r.issues
        if not r.feasible
    ]

    return AggregatedPlatformReview(
        platform_review_result=reviews,
        has_blocking_issue=any(not r.feasible for r in reviews),
        blocking_reasons=blocking,
    )


def _parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)
