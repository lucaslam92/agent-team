from __future__ import annotations
import json
from aadh.core.llm import LLMClient
from prd_pipeline.models import RequirementBrief
from prd_pipeline.skills import prd_parse


def run(client: LLMClient, raw_input: str, source: str) -> RequirementBrief:
    raw = client.chat(
        system=prd_parse.SYSTEM,
        user=prd_parse.user_prompt(raw_input, source),
    )
    d = _parse(raw)
    return RequirementBrief(
        feature_goal=d.get("feature_goal", ""),
        user_flow=d.get("user_flow", []),
        acceptance_criteria=d.get("acceptance_criteria", []),
        platforms=d.get("platforms", []),
        raw_notes=d.get("raw_notes", []),
    )


def _parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)
