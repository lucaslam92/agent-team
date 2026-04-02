from __future__ import annotations
import json
from aadh.core.llm import LLMClient
from prd_pipeline.models import (
    RequirementBrief, ContextBlock, CompletenessReport, GateStatus, RiskLevel
)
from prd_pipeline.skills import completeness_check


def run(client: LLMClient, brief: RequirementBrief, context: ContextBlock) -> CompletenessReport:
    raw = client.chat(
        system=completeness_check.SYSTEM,
        user=completeness_check.user_prompt(brief, context),
    )
    d = _parse(raw)
    return CompletenessReport(
        status=GateStatus(d.get("status", "blocked")),
        missing_info=d.get("missing_info", []),
        assumptions=d.get("assumptions", []),
        risk_level=RiskLevel(d.get("risk_level", "high")),
    )


def _parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)
