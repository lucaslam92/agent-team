from __future__ import annotations
import json
from aadh.core.llm import LLMClient
from prd_pipeline.models import (
    FigmaBundle, FigmaLayoutResult, FigmaScreen,
    FigmaInteractionResult, FigmaInteraction,
)
from prd_pipeline.skills import figma_review


def run(client: LLMClient, figma_data: dict) -> FigmaBundle:
    # Layout
    raw_layout = client.chat(
        system=figma_review.LAYOUT_SYSTEM,
        user=figma_review.layout_user_prompt(figma_data),
    )
    layout_d = _parse(raw_layout).get("layout", {})
    screens = [
        FigmaScreen(name=s.get("name", ""), components=s.get("components", []))
        for s in layout_d.get("screens", [])
    ]

    # Interactions
    raw_ixn = client.chat(
        system=figma_review.INTERACTION_SYSTEM,
        user=figma_review.interaction_user_prompt(figma_data),
    )
    ixn_d = _parse(raw_ixn)
    interactions = [
        FigmaInteraction(
            trigger=i.get("trigger", ""),
            action=i.get("action", ""),
            target_screen=i.get("target_screen", ""),
        )
        for i in ixn_d.get("interactions", [])
    ]

    return FigmaBundle(
        layout=FigmaLayoutResult(screens=screens),
        interactions=FigmaInteractionResult(interactions=interactions),
    )


def _parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)
