"""
PRD Pipeline — all JSON-serializable data models.

Every role receives and returns exactly one of these typed dataclasses.
No role ever accesses global state.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Shared enums ──────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class GateStatus(str, Enum):
    CONTINUE = "continue"
    BLOCKED  = "blocked"


class Platform(str, Enum):
    ANDROID = "android"
    IOS     = "ios"
    WEB     = "web"
    BACKEND = "backend"


# ── Stage 1 output ────────────────────────────────────────────────────────────

@dataclass
class RequirementBrief:
    """Output of Requirement Parser."""
    feature_goal: str
    user_flow: list[str]
    acceptance_criteria: list[str]
    platforms: list[str]           # ["android", "ios", "web", "backend"]
    raw_notes: list[str]


# ── Stage 2 output ────────────────────────────────────────────────────────────

@dataclass
class ContextBlock:
    related_modules: list[str]
    existing_features: list[str]
    constraints: list[str]


@dataclass
class EnrichedRequirement:
    """Output of Knowledge Injector."""
    requirement_brief: RequirementBrief
    context: ContextBlock


@dataclass
class CompletenessReport:
    """Output of Completeness Checker (Gate 1)."""
    status: GateStatus
    missing_info: list[str]
    assumptions: list[str]
    risk_level: RiskLevel


# ── Stage 3 output (optional) ─────────────────────────────────────────────────

@dataclass
class FigmaScreen:
    name: str
    components: list[str]


@dataclass
class FigmaLayoutResult:
    """Output of Figma Layout Reviewer."""
    screens: list[FigmaScreen]


@dataclass
class FigmaInteraction:
    trigger: str
    action: str
    target_screen: str


@dataclass
class FigmaInteractionResult:
    """Output of Figma Interaction Reviewer."""
    interactions: list[FigmaInteraction]


@dataclass
class FigmaBundle:
    """Combined figma input/output passed downstream."""
    layout: FigmaLayoutResult | None = None
    interactions: FigmaInteractionResult | None = None


# ── Stage 4 output ────────────────────────────────────────────────────────────

@dataclass
class PlatformReview:
    """Output of any Platform Reviewer (Android / iOS / Web / Backend)."""
    platform: Platform
    feasible: bool
    issues: list[str]
    constraints: list[str]
    required_changes: list[str]
    risk_level: RiskLevel


@dataclass
class AggregatedPlatformReview:
    """Output of Platform Review Aggregator."""
    platform_review_result: list[PlatformReview]
    has_blocking_issue: bool
    blocking_reasons: list[str]


# ── Stage 5 output ────────────────────────────────────────────────────────────

@dataclass
class ArchitectDecision:
    """Output of Domain Architect."""
    final_decisions: list[str]
    adjusted_features: list[str]
    tradeoffs: list[str]
    resolved_constraints: list[str]


# ── Stage 6 output ────────────────────────────────────────────────────────────

@dataclass
class FeatureFlow:
    user_flow: list[str]
    expected_behavior: list[str]
    edge_cases: list[str]


@dataclass
class FeatureImplementation:
    approach: str
    platform_alignment: dict[str, str]   # platform → implementation note
    constraints: list[str]


@dataclass
class Feature:
    name: str
    flow: FeatureFlow
    implementation: FeatureImplementation


@dataclass
class FinalPRD:
    """
    The final executable contract.
    Gate 3 validates this before accepting it.
    """
    features: list[Feature]
    acceptance_criteria: list[str]


# ── Pipeline context (threaded through all stages) ────────────────────────────

@dataclass
class PipelineContext:
    """
    Carries accumulated state across stages.
    Each stage reads what it needs and adds its own output.
    """
    raw_input: str
    source: str                                    # "prd" | "issue" | "text"

    # Outputs accumulated stage by stage
    requirement_brief:    RequirementBrief | None            = None
    enriched_requirement: EnrichedRequirement | None         = None
    completeness_report:  CompletenessReport | None          = None
    figma:                FigmaBundle | None                 = None
    platform_reviews:     AggregatedPlatformReview | None    = None
    architect_decision:   ArchitectDecision | None           = None
    final_prd:            FinalPRD | None                    = None

    # Gate outcomes
    gate1_passed: bool = False
    gate2_passed: bool = False
    gate3_passed: bool = False

    errors: list[str] = field(default_factory=list)
