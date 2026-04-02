from __future__ import annotations
import json
from aadh.core.llm import LLMClient
from prd_pipeline.models import (
    RequirementBrief, ArchitectDecision, AggregatedPlatformReview,
    FinalPRD, Feature, FeatureFlow, FeatureImplementation,
)
from prd_pipeline.skills import final_prd_compile


def run(
    client: LLMClient,
    brief: RequirementBrief,
    architect_decision: ArchitectDecision,
    platform_reviews: AggregatedPlatformReview,
) -> FinalPRD:
    raw = client.chat(
        system=final_prd_compile.SYSTEM,
        user=final_prd_compile.user_prompt(brief, architect_decision, platform_reviews),
        max_tokens=8192,
    )
    d = _parse(raw)

    features: list[Feature] = []
    for f in d.get("features", []):
        flow_data  = f.get("flow", {})
        impl_data  = f.get("implementation", {})
        features.append(Feature(
            name=f.get("name", ""),
            flow=FeatureFlow(
                user_flow=flow_data.get("user_flow", []),
                expected_behavior=flow_data.get("expected_behavior", []),
                edge_cases=flow_data.get("edge_cases", []),
            ),
            implementation=FeatureImplementation(
                approach=impl_data.get("approach", ""),
                platform_alignment=impl_data.get("platform_alignment", {}),
                constraints=impl_data.get("constraints", []),
            ),
        ))

    return FinalPRD(
        features=features,
        acceptance_criteria=d.get("acceptance_criteria", []),
    )


def _parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)
