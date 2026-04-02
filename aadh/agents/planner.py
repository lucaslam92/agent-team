"""
Planner Agent — Produces a structured plan from a natural-language task.

Outputs:
  - Which files to read/modify
  - Acceptance criteria
  - A ready-to-run Maestro YAML flow for verification
  - Risk points

The planner DOES NOT prescribe implementation — that's the Coder's job.
On retry, it adjusts based on Evaluator feedback.
"""

from __future__ import annotations
import json
import anthropic

from aadh.core.models import Plan


def plan(
    client: anthropic.Anthropic,
    task: str,
    project_path: str,
    app_package: str,
    main_activity: str,
    feedback: str | None = None,
) -> Plan:
    system = """\
You are a planning agent for an Android development harness.
Given a development task, output a structured JSON plan.

Rules:
1. List only the files that MUST be changed — no extras.
2. Acceptance criteria must be user-observable (what the user sees/can do).
3. The maestro_flow must be valid YAML that Maestro can run directly.
4. Risk points should flag non-obvious failure modes.
5. If feedback is provided, ADJUST the plan — do NOT just repeat the old one.

Respond with ONLY valid JSON (no markdown fences), matching this schema exactly:
{
  "task": "string",
  "modules": ["string"],
  "files": ["relative/path/to/File.kt"],
  "acceptance_criteria": ["string"],
  "verification_steps": ["string"],
  "risk_points": ["string"],
  "maestro_flow": "# valid maestro YAML string"
}"""

    user_parts = [
        f"Task: {task}",
        f"Project root: {project_path}",
        f"App package: {app_package}",
        f"Main activity: {main_activity}",
    ]
    if feedback:
        user_parts += ["", f"Evaluator feedback from last run:\n{feedback}"]

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": "\n".join(user_parts)}],
    ) as stream:
        response = stream.get_final_message()

    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)

    return Plan(
        task=data["task"],
        modules=data.get("modules", ["app"]),
        files=data.get("files", []),
        acceptance_criteria=data.get("acceptance_criteria", []),
        verification_steps=data.get("verification_steps", []),
        risk_points=data.get("risk_points", []),
        maestro_flow=data.get("maestro_flow", ""),
    )
