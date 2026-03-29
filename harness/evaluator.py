"""
Evaluator Agent — Score on specific dimensions. Never generate.

Key principle: generation and evaluation MUST be separated.
A model asked to both generate and evaluate its own output
will rationalize rather than critique. The evaluator's only job
is to be a ruthless judge — it does not produce improvements.

Inspired by GAN discriminator thinking: the evaluator makes the
generator better by being harder to fool, not by telling it what to do.
"""

import anthropic
from dataclasses import dataclass
from harness.generator import GeneratorOutput


@dataclass
class Dimension:
    name: str
    description: str
    weight: float  # 0.0–1.0, sum across dimensions should equal 1.0


@dataclass
class DimensionScore:
    dimension: Dimension
    score: float          # 0–10
    rationale: str
    blocking_issues: list[str]


@dataclass
class EvaluationResult:
    output: GeneratorOutput
    dimension_scores: list[DimensionScore]
    weighted_score: float   # 0–10
    passed: bool
    feedback_for_generator: str  # Concrete, actionable — NOT a rewrite
    feedback_for_planner: str    # Should direction change?


# Default evaluation dimensions. Swap these per project type.
DEFAULT_DIMENSIONS = [
    Dimension("correctness",    "Does it work? Are there obvious bugs or logic errors?",           0.30),
    Dimension("completeness",   "Is the artifact production-ready, not a skeleton?",               0.25),
    Dimension("constraints",    "Are all planner constraints honored?",                            0.25),
    Dimension("quality",        "Code style, clarity, error handling, edge cases.",                0.20),
]


def evaluate(
    client: anthropic.Anthropic,
    output: GeneratorOutput,
    dimensions: list[Dimension] | None = None,
    pass_threshold: float = 7.5,
) -> EvaluationResult:
    """
    Score the generator's output on each dimension independently.
    Return structured feedback that the orchestrator can route back
    to the generator (and optionally the planner).

    The evaluator NEVER suggests rewrites — only diagnosis.
    """
    dims = dimensions or DEFAULT_DIMENSIONS

    system = """\
You are an evaluator agent in a multi-agent harness.
Your role: judge an artifact against specific dimensions. You do NOT generate or fix code.

Rules:
1. Score each dimension 0–10 independently. Do not let one dimension bias another.
2. List specific blocking issues (not style nits) that prevent a higher score.
3. Your feedback must be diagnostic, not prescriptive. Describe WHAT is wrong, not HOW to fix it.
4. Be brutal. A 7/10 means "mostly works but has real problems." Reserve 9-10 for exceptional work.
5. feedback_for_generator: 3-6 bullet points of concrete issues. No rewrites, no code snippets.
6. feedback_for_planner: 1-2 sentences — should the direction change, or is this a generator execution problem?

Respond in this exact JSON format (no markdown fences):
{
  "dimensions": [
    {
      "name": "<dimension name>",
      "score": <0-10>,
      "rationale": "...",
      "blocking_issues": ["...", "..."]
    }
  ],
  "feedback_for_generator": "...",
  "feedback_for_planner": "..."
}"""

    dims_desc = "\n".join(f"- {d.name} (weight {d.weight:.0%}): {d.description}" for d in dims)

    user_content = f"""\
Goal: {output.plan.goal}
Direction given to generator: {output.plan.direction}
Constraints: {', '.join(output.plan.constraints)}
Quality bar: {output.plan.quality_bar}

=== ARTIFACT (iteration {output.iteration}) ===
{output.artifact}

=== GENERATOR SELF NOTES ===
{output.self_notes}

=== EVALUATION DIMENSIONS ===
{dims_desc}

Score this artifact on each dimension."""

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        response = stream.get_final_message()

    import json
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)

    dim_map = {d.name: d for d in dims}
    dimension_scores = []
    for ds in data["dimensions"]:
        dim = dim_map.get(ds["name"])
        if not dim:
            continue
        dimension_scores.append(DimensionScore(
            dimension=dim,
            score=float(ds["score"]),
            rationale=ds["rationale"],
            blocking_issues=ds.get("blocking_issues", []),
        ))

    weighted_score = sum(
        ds.score * ds.dimension.weight
        for ds in dimension_scores
    )

    return EvaluationResult(
        output=output,
        dimension_scores=dimension_scores,
        weighted_score=weighted_score,
        passed=weighted_score >= pass_threshold,
        feedback_for_generator=data["feedback_for_generator"],
        feedback_for_planner=data["feedback_for_planner"],
    )
