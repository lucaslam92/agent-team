"""
PRD Pipeline Orchestrator.

Executes the staged pipeline:
  Stage 1 → Stage 2 → Gate 1 → Stage 3 (optional) → Stage 4 → Gate 2 → Stage 5 → Stage 6 → Gate 3

Each stage receives only the fields it needs.
Gates are explicit — no role decides whether to proceed.
"""

from __future__ import annotations
import json
from pathlib import Path
from dataclasses import asdict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from aadh.core.llm import LLMClient, client_from_settings
from prd_pipeline.models import (
    PipelineContext, FigmaBundle, Platform, GateStatus,
)
from prd_pipeline.roles import (
    requirement_parser, knowledge_injector, completeness_checker,
    platform_reviewer, domain_architect, final_compiler,
)
from prd_pipeline import gates


class PipelineBlocked(Exception):
    """Raised when a Gate stops the pipeline."""
    def __init__(self, gate: str, reason: str):
        self.gate   = gate
        self.reason = reason
        super().__init__(f"{gate} blocked: {reason}")


def run(
    raw_input: str,
    source: str,
    settings: dict,
    figma_data: dict | None = None,
    output_dir: Path | None = None,
    verbose: bool = True,
) -> PipelineContext:
    console = Console() if verbose else None
    ctx = PipelineContext(raw_input=raw_input, source=source)

    llm_cfg = settings.get("llm", {})

    def make_client(role_name: str = "default") -> LLMClient:
        return client_from_settings(
            llm_cfg.get(role_name, {}),
            llm_cfg.get("default", {}),
        )

    if console:
        console.print(Panel(
            f"[bold cyan]PRD Pipeline[/bold cyan]\n"
            f"Source: {source}  |  Input: {raw_input[:80]}{'…' if len(raw_input) > 80 else ''}",
            box=box.ROUNDED,
        ))

    # ── Stage 1: Requirement Parser ───────────────────────────────────────────
    _log(console, "Stage 1", "Requirement Parser")
    ctx.requirement_brief = requirement_parser.run(
        make_client("parser"), raw_input, source
    )
    _ok(console, f"Goal: {ctx.requirement_brief.feature_goal[:80]}")

    # ── Stage 2a: Knowledge Injector ──────────────────────────────────────────
    _log(console, "Stage 2a", "Knowledge Injector")
    enriched = knowledge_injector.run(make_client("injector"), ctx.requirement_brief)
    ctx.enriched_requirement = enriched
    _ok(console, f"{len(enriched.context.related_modules)} related modules found")

    # ── Stage 2b: Completeness Checker + Gate 1 ───────────────────────────────
    _log(console, "Stage 2b", "Completeness Checker")
    ctx.completeness_report = completeness_checker.run(
        make_client("checker"),
        ctx.requirement_brief,
        enriched.context,
    )
    g1 = gates.gate1_completeness(ctx.completeness_report)
    ctx.gate1_passed = g1.passed
    if not g1.passed:
        _fail(console, f"Gate 1 BLOCKED\n{g1.reason}")
        raise PipelineBlocked("Gate 1", g1.reason)
    _ok(console, f"Gate 1 passed  (risk: {ctx.completeness_report.risk_level.value})")

    # ── Stage 3: Figma (optional) ─────────────────────────────────────────────
    if figma_data:
        from prd_pipeline.roles import figma_reviewer
        _log(console, "Stage 3", "Figma Reviewer")
        ctx.figma = figma_reviewer.run(make_client("figma"), figma_data)
        _ok(console, "Figma layout + interactions extracted")
    else:
        ctx.figma = FigmaBundle()

    # ── Stage 4: Platform Reviewers (parallel) + Gate 2 ──────────────────────
    platforms = ctx.requirement_brief.platforms or ["android"]
    _log(console, "Stage 4", f"Platform Reviewers: {', '.join(platforms)}")
    ctx.platform_reviews = platform_reviewer.run_all(
        make_client=lambda p: make_client(f"reviewer_{p}"),
        platforms=platforms,
        brief=ctx.requirement_brief,
        context=enriched.context,
    )
    g2 = gates.gate2_platform_review(ctx.platform_reviews)
    ctx.gate2_passed = g2.passed
    if not g2.passed:
        _fail(console, f"Gate 2 BLOCKED\n{g2.reason}")
        raise PipelineBlocked("Gate 2", g2.reason)
    _ok(console, "Gate 2 passed — all platforms feasible")

    if console:
        _print_platform_table(console, ctx.platform_reviews.platform_review_result)

    # ── Stage 5: Domain Architect ─────────────────────────────────────────────
    _log(console, "Stage 5", "Domain Architect")
    ctx.architect_decision = domain_architect.run(
        make_client("architect"),
        brief=ctx.requirement_brief,
        platform_reviews=ctx.platform_reviews.platform_review_result,
        figma=ctx.figma,
    )
    _ok(console, f"{len(ctx.architect_decision.final_decisions)} decisions made")

    # ── Stage 6: Final PRD Compiler + Gate 3 ─────────────────────────────────
    _log(console, "Stage 6", "Final PRD Compiler")
    ctx.final_prd = final_compiler.run(
        make_client("compiler"),
        brief=ctx.requirement_brief,
        architect_decision=ctx.architect_decision,
        platform_reviews=ctx.platform_reviews,
    )
    g3 = gates.gate3_final_prd(ctx.final_prd)
    ctx.gate3_passed = g3.passed
    if not g3.passed:
        _fail(console, f"Gate 3 BLOCKED\n{g3.reason}")
        raise PipelineBlocked("Gate 3", g3.reason)
    _ok(console, f"Gate 3 passed — {len(ctx.final_prd.features)} feature(s), "
                 f"{len(ctx.final_prd.acceptance_criteria)} criteria")

    # ── Write output ──────────────────────────────────────────────────────────
    if output_dir:
        _write_outputs(output_dir, ctx)
        if console:
            console.print(f"\n[dim]Outputs written to {output_dir}[/dim]")

    return ctx


# ── Output writers ────────────────────────────────────────────────────────────

def _write_outputs(output_dir: Path, ctx: PipelineContext) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    if ctx.final_prd:
        _write_json(output_dir / "final_prd.json", _prd_to_dict(ctx.final_prd))
        _write_markdown(output_dir / "final_prd.md", ctx.final_prd)

    if ctx.completeness_report:
        _write_json(output_dir / "completeness_report.json", {
            "status":       ctx.completeness_report.status.value,
            "missing_info": ctx.completeness_report.missing_info,
            "assumptions":  ctx.completeness_report.assumptions,
            "risk_level":   ctx.completeness_report.risk_level.value,
        })

    if ctx.architect_decision:
        _write_json(output_dir / "architect_decision.json", {
            "final_decisions":      ctx.architect_decision.final_decisions,
            "adjusted_features":    ctx.architect_decision.adjusted_features,
            "tradeoffs":            ctx.architect_decision.tradeoffs,
            "resolved_constraints": ctx.architect_decision.resolved_constraints,
        })


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _prd_to_dict(prd) -> dict:
    return {
        "features": [
            {
                "name": f.name,
                "flow": {
                    "user_flow":          f.flow.user_flow,
                    "expected_behavior":  f.flow.expected_behavior,
                    "edge_cases":         f.flow.edge_cases,
                },
                "implementation": {
                    "approach":            f.implementation.approach,
                    "platform_alignment":  f.implementation.platform_alignment,
                    "constraints":         f.implementation.constraints,
                },
            }
            for f in prd.features
        ],
        "acceptance_criteria": prd.acceptance_criteria,
    }


def _write_markdown(path: Path, prd) -> None:
    lines = ["# Final PRD", ""]
    for f in prd.features:
        lines += [f"## Feature: {f.name}", ""]
        lines += ["### User Flow"]
        lines += [f"1. {s}" for s in f.flow.user_flow]
        lines += ["", "### Expected Behavior"]
        lines += [f"- {b}" for b in f.flow.expected_behavior]
        lines += ["", "### Edge Cases"]
        lines += [f"- {e}" for e in f.flow.edge_cases]
        lines += ["", "### Implementation", f"_{f.implementation.approach}_", ""]
        lines += ["**Platform Alignment:**"]
        for plat, note in f.implementation.platform_alignment.items():
            lines.append(f"- **{plat}**: {note}")
        lines += ["", "**Constraints:**"]
        lines += [f"- {c}" for c in f.implementation.constraints]
        lines += [""]
    lines += ["## Acceptance Criteria"]
    lines += [f"- {c}" for c in prd.acceptance_criteria]
    path.write_text("\n".join(lines), encoding="utf-8")


# ── Console helpers ───────────────────────────────────────────────────────────

def _log(c, stage, msg): c and c.print(f"[bold yellow][{stage}][/bold yellow] {msg}")
def _ok(c, msg):         c and c.print(f"  [green]✓[/green] {msg}")
def _fail(c, msg):       c and c.print(f"  [red]✗[/red] {msg}")


def _print_platform_table(console, reviews):
    t = Table(box=box.SIMPLE, show_header=True)
    t.add_column("Platform")
    t.add_column("Feasible", justify="center")
    t.add_column("Risk")
    t.add_column("Issues", justify="right")
    for r in reviews:
        f_str = "[green]Yes[/green]" if r.feasible else "[red]No[/red]"
        t.add_row(r.platform.value, f_str, r.risk_level.value, str(len(r.issues)))
    console.print(t)
