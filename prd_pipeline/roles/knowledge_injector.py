from __future__ import annotations
import json
from aadh.core.llm import LLMClient
from prd_pipeline.models import RequirementBrief, ContextBlock, EnrichedRequirement
from prd_pipeline.skills import context_injection


def run(client: LLMClient, brief: RequirementBrief) -> EnrichedRequirement:
    raw = client.chat(
        system=context_injection.SYSTEM,
        user=context_injection.user_prompt(brief),
    )
    d = _parse(raw)
    ctx = d.get("context", {})
    return EnrichedRequirement(
        requirement_brief=brief,
        context=ContextBlock(
            related_modules=ctx.get("related_modules", []),
            existing_features=ctx.get("existing_features", []),
            constraints=ctx.get("constraints", []),
        ),
    )


def _parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)
