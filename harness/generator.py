"""
Generator Agent — Produce artifacts from direction.

Key principle: the generator owns ALL implementation decisions.
It receives direction + constraints from the planner and evaluator
feedback from previous rounds, but never receives a prescriptive
"do X then Y then Z" recipe. That freedom is what makes it
capable of finding non-obvious solutions.
"""

import anthropic
from dataclasses import dataclass, field
from harness.planner import Plan


@dataclass
class GeneratorOutput:
    artifact: str               # The generated code / content
    self_notes: str             # Generator's own commentary on tradeoffs made
    plan: Plan
    iteration: int


def generate(
    client: anthropic.Anthropic,
    plan: Plan,
    previous_output: GeneratorOutput | None = None,
    evaluator_feedback: str | None = None,
) -> GeneratorOutput:
    """
    Generate an artifact given a plan direction.
    On subsequent iterations, receives structured evaluator feedback
    and its own previous output so it can improve rather than start over.
    """
    system = """\
You are a generator agent in a multi-agent harness.
Your role: produce a complete, working artifact.

Rules:
1. The planner gave you direction and constraints — honor them.
2. You own ALL implementation decisions. Be creative within constraints.
3. Produce COMPLETE artifacts. Partial / skeleton code fails evaluation.
4. After the artifact, add a brief "## Self Notes" section explaining key tradeoffs.

Output format:
```python
<complete code here>
```
## Self Notes
<2-4 sentences on tradeoffs, design decisions, limitations>"""

    messages: list[dict] = []

    user_parts = [
        f"Direction: {plan.direction}",
        "",
        "Constraints (non-negotiable):",
        *[f"- {c}" for c in plan.constraints],
        "",
        f"Quality bar: {plan.quality_bar}",
    ]

    if previous_output and evaluator_feedback:
        user_parts += [
            "",
            "--- ITERATION FEEDBACK ---",
            f"Your previous attempt (iteration {previous_output.iteration}):",
            "```python",
            previous_output.artifact,
            "```",
            "",
            "Evaluator feedback:",
            evaluator_feedback,
            "",
            "Produce an improved version. You may restructure freely.",
        ]

    messages.append({"role": "user", "content": "\n".join(user_parts)})

    full_text = ""
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            full_text += text
        response = stream.get_final_message()

    # Extract code block
    import re
    code_match = re.search(r"```python\n(.*?)```", full_text, re.DOTALL)
    artifact = code_match.group(1).strip() if code_match else full_text

    # Extract self notes
    notes_match = re.search(r"## Self Notes\n(.*?)$", full_text, re.DOTALL)
    self_notes = notes_match.group(1).strip() if notes_match else ""

    iteration = (previous_output.iteration + 1) if previous_output else 1

    return GeneratorOutput(
        artifact=artifact,
        self_notes=self_notes,
        plan=plan,
        iteration=iteration,
    )
