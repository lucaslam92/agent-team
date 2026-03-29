"""
Planner Agent — Direction, not path.

Key principle: upstream planning must be restrained.
Give the model a destination, not turn-by-turn navigation.
Over-specifying plans collapses the generator's solution space
and makes the harness brittle.
"""

import anthropic
from dataclasses import dataclass


@dataclass
class Plan:
    goal: str
    direction: str          # High-level intent (NOT step-by-step instructions)
    constraints: list[str]  # Hard limits the generator must respect
    quality_bar: str        # Plain-language description of "good enough"
    iteration: int = 0


def plan(client: anthropic.Anthropic, goal: str, feedback: str | None = None) -> Plan:
    """
    Produce a high-level direction for a given goal.
    On subsequent iterations, incorporate evaluator feedback to adjust direction.

    The planner intentionally avoids prescribing implementation details —
    that is the generator's domain.
    """
    system = """\
You are a planning agent in a multi-agent harness.
Your role: translate a goal into a HIGH-LEVEL DIRECTION — not a step-by-step plan.

Rules you must follow:
1. Describe WHERE to go, not HOW to get there. No pseudocode, no file lists, no function names.
2. Keep direction to 2-4 sentences. Every extra sentence is a constraint you're imposing on the generator.
3. Extract the 3-5 hardest constraints (things that are non-negotiable).
4. State the quality bar in plain language (what does "done well" look like to a user?).
5. If feedback is provided, adjust direction — do NOT just repeat the original plan.

Respond in this exact JSON format (no markdown fences):
{
  "direction": "...",
  "constraints": ["...", "..."],
  "quality_bar": "..."
}"""

    user_content = f"Goal: {goal}"
    if feedback:
        user_content += f"\n\nEvaluator feedback from last attempt:\n{feedback}"

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        response = stream.get_final_message()

    import json
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)

    return Plan(
        goal=goal,
        direction=data["direction"],
        constraints=data["constraints"],
        quality_bar=data["quality_bar"],
    )
