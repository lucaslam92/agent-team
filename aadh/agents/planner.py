"""
Planner Agent — TaskSpec → structured plan + Maestro verification flow.

Accepts input from any source (Jira, Confluence, Markdown, plain text)
via the unified TaskSpec — the Planner itself is source-agnostic.

Output: plan.json (written by ArtifactStore) + Plan dataclass.
"""

from __future__ import annotations
import json

from aadh.core.llm import LLMClient
from aadh.core.models import Plan
from aadh.input.parser import TaskSpec


SYSTEM = """\
You are a planning agent for an Android development automation harness.

Your job:
1. Identify which source files need to change.
2. Write clear, user-observable acceptance criteria.
3. Write a valid Maestro YAML test flow that verifies the criteria.
4. Flag risk points (things likely to go wrong).

Rules:
- List only files that MUST be modified — no extras.
- Never describe HOW to implement — that is the Coder's job.
- Acceptance criteria must describe what a human user would see or be able to do.
- Maestro flow must use `text:` or `id:` selectors (prefer `text:` for stability).
- maestro_flow must be a complete, runnable YAML string.
- If feedback is provided, adjust the plan — do NOT repeat the failed plan verbatim.

Respond with ONLY valid JSON, no markdown fences, matching this schema exactly:
{
  "task": "string — restate the task concisely",
  "modules": ["app"],
  "files": ["relative/path/from/project/root/File.kt"],
  "acceptance_criteria": ["User can see X", "Tapping Y shows Z"],
  "verification_steps": ["human-readable steps matching maestro flow"],
  "risk_points": ["string"],
  "maestro_flow": "appId: com.example.app\\n---\\n- launchApp\\n- tapOn:\\n    text: ..."
}"""


def plan(
    client: LLMClient,
    spec: TaskSpec,
    project_path: str,
    app_package: str,
    main_activity: str,
    feedback: str | None = None,
) -> Plan:
    parts = [
        f"Task title: {spec.title}",
        "",
        f"Full description:\n{spec.description}",
        "",
        f"Android project root: {project_path}",
        f"App package: {app_package}",
        f"Main activity class: {main_activity}",
    ]

    # Surface useful metadata (Jira priority/labels, etc.)
    if spec.metadata:
        useful = {k: v for k, v in spec.metadata.items()
                  if v and k not in ("issue_key", "page_id")}
        if useful:
            parts += ["", "Context metadata:"]
            parts += [f"  {k}: {v}" for k, v in useful.items()]

    if spec.source_url:
        parts += ["", f"Source: {spec.source_url}"]

    if feedback:
        parts += ["", "=== EVALUATOR FEEDBACK FROM LAST RUN ===", feedback]

    raw = client.chat(system=SYSTEM, user="\n".join(parts))

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    data = json.loads(raw)

    return Plan(
        task=data.get("task", spec.title),
        modules=data.get("modules", ["app"]),
        files=data.get("files", []),
        acceptance_criteria=data.get("acceptance_criteria", []),
        verification_steps=data.get("verification_steps", []),
        risk_points=data.get("risk_points", []),
        maestro_flow=data.get("maestro_flow", ""),
    )
