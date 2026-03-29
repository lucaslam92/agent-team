"""
Orchestrator — Wires planner → generator → evaluator into a loop.

Key insight from the Harness Engineering approach:
- Single-agent: fast but fragile ("一点就碎" — shatters on first touch)
- Harness: slower but reliable output
- The loop runs until the evaluator passes or max_iterations is reached
- Each component is independently swappable as models improve
"""

import anthropic
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from harness.planner import Plan, plan as run_planner
from harness.generator import GeneratorOutput, generate as run_generator
from harness.evaluator import (
    EvaluationResult,
    Dimension,
    DEFAULT_DIMENSIONS,
    evaluate as run_evaluator,
)


@dataclass
class HarnessResult:
    goal: str
    artifact: str
    final_score: float
    iterations: int
    passed: bool
    history: list[EvaluationResult]


def run(
    goal: str,
    max_iterations: int = 4,
    pass_threshold: float = 7.5,
    dimensions: list[Dimension] | None = None,
    api_key: str | None = None,
    verbose: bool = True,
) -> HarnessResult:
    """
    Run the full planner → generator → evaluator harness.

    Args:
        goal:            What to build (high-level user intent)
        max_iterations:  Hard cap on attempts (cost guard)
        pass_threshold:  Weighted score (0–10) that counts as passing
        dimensions:      Custom evaluation criteria (defaults to DEFAULT_DIMENSIONS)
        api_key:         Anthropic API key (falls back to ANTHROPIC_API_KEY env var)
        verbose:         Print progress to console
    """
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    console = Console() if verbose else None

    dims = dimensions or DEFAULT_DIMENSIONS
    history: list[EvaluationResult] = []

    current_plan: Plan | None = None
    current_output: GeneratorOutput | None = None
    evaluator_feedback: str | None = None
    planner_feedback: str | None = None

    if console:
        console.print(Panel(f"[bold cyan]Harness Engineering[/bold cyan]\nGoal: {goal}",
                            box=box.ROUNDED))

    for iteration in range(1, max_iterations + 1):
        # ── 1. PLAN (restrained: direction only) ──────────────────────────
        if console:
            console.print(f"\n[bold yellow]▶ Iteration {iteration}/{max_iterations}[/bold yellow]")
            console.print("[dim]Planner: generating direction...[/dim]")

        current_plan = run_planner(client, goal, feedback=planner_feedback)

        if console:
            console.print(f"[green]Direction:[/green] {current_plan.direction}")

        # ── 2. GENERATE ───────────────────────────────────────────────────
        if console:
            console.print("[dim]Generator: producing artifact...[/dim]")

        current_output = run_generator(
            client,
            current_plan,
            previous_output=current_output,
            evaluator_feedback=evaluator_feedback,
        )

        if console:
            lines = current_output.artifact.count("\n") + 1
            console.print(f"[green]Artifact:[/green] {lines} lines generated")

        # ── 3. EVALUATE (scores specific dimensions, never generates) ─────
        if console:
            console.print("[dim]Evaluator: scoring on dimensions...[/dim]")

        result = run_evaluator(
            client,
            current_output,
            dimensions=dims,
            pass_threshold=pass_threshold,
        )
        history.append(result)

        evaluator_feedback = result.feedback_for_generator
        planner_feedback = result.feedback_for_planner

        if console:
            _print_scores(console, result)

        if result.passed:
            if console:
                console.print(f"\n[bold green]✓ Passed on iteration {iteration} "
                              f"(score {result.weighted_score:.1f}/10)[/bold green]")
            break
    else:
        if console:
            console.print(f"\n[bold red]✗ Did not pass in {max_iterations} iterations. "
                          f"Best score: {max(h.weighted_score for h in history):.1f}/10[/bold red]")

    best = max(history, key=lambda h: h.weighted_score)

    return HarnessResult(
        goal=goal,
        artifact=best.output.artifact,
        final_score=best.weighted_score,
        iterations=len(history),
        passed=best.passed,
        history=history,
    )


def _print_scores(console: Console, result: EvaluationResult) -> None:
    table = Table(box=box.SIMPLE_HEAVY, show_header=True)
    table.add_column("Dimension", style="cyan")
    table.add_column("Weight", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Key Issues", style="dim")

    for ds in result.dimension_scores:
        score_str = f"[green]{ds.score:.1f}[/green]" if ds.score >= 7.5 else \
                    f"[yellow]{ds.score:.1f}[/yellow]" if ds.score >= 5.0 else \
                    f"[red]{ds.score:.1f}[/red]"
        issues = "; ".join(ds.blocking_issues[:2]) if ds.blocking_issues else "—"
        table.add_row(
            ds.dimension.name,
            f"{ds.dimension.weight:.0%}",
            score_str,
            issues[:60] + "…" if len(issues) > 60 else issues,
        )

    status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
    table.add_row("", "", f"{status} [bold]{result.weighted_score:.1f}[/bold]", "", end_section=True)
    console.print(table)

    if not result.passed:
        console.print(f"[yellow]Generator feedback:[/yellow] {result.feedback_for_generator}")
