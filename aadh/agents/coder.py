"""
Coder Agent — Full-file read strategy for maximum accuracy.

Strategy (accuracy over token economy):
  1. Read every file listed in the plan from disk, in full.
  2. Pass ALL file contents to the LLM in a single context window.
  3. LLM returns complete replacement content for each file that needs changing.
  4. Write replacements back to disk.
  5. Generate diff for artifacts.

Why full-file?
  Partial patch generation causes misaligned line numbers, wrong context,
  and hallucinated code. Seeing the whole file lets the model reason about
  imports, class hierarchy, and side effects correctly.

On retry: the LLM also receives the Evaluator's diagnostic feedback so it
can target the exact failure — without the Evaluator prescribing a fix.
"""

from __future__ import annotations
import json
import difflib
from pathlib import Path

from aadh.core.llm import LLMClient
from aadh.core.models import Plan, CoderOutput, CodeChange


SYSTEM = """\
You are a code-modification agent for an Android development harness.

You will receive:
- The development task
- Acceptance criteria
- Risk points from the planner
- The COMPLETE content of every file you are allowed to change
- (On retries) Diagnostic feedback from the evaluator

Your job: produce complete, working replacements for files that need changing.

Rules:
1. Return ONLY JSON — no explanation, no markdown fences.
2. For each file you modify, provide the COMPLETE new content (not a patch).
3. If a file does NOT need changes, omit it from the output.
4. Do not modify files not listed in "allowed_files".
5. Write production-quality code: handle null checks, edge cases, imports.
6. Every change must be necessary to satisfy the acceptance criteria.
7. Feedback is a diagnosis — it tells you WHAT is wrong, not HOW to fix it.
   Reason through the fix yourself.

Response schema (strict JSON, no fences):
{
  "changes": [
    {
      "file_path": "relative/path/File.kt",
      "content": "complete new file content as a string",
      "rationale": "one sentence: why this change was needed"
    }
  ],
  "change_summary": "2-4 sentence summary of what was changed and why"
}"""


def code(
    client: LLMClient,
    plan: Plan,
    project_path: Path,
    iteration: int,
    evaluator_feedback: str | None = None,
    max_files: int = 5,
) -> CoderOutput:
    if len(plan.files) > max_files:
        raise ValueError(
            f"Plan lists {len(plan.files)} files but max_files={max_files}. "
            "Reduce scope or raise max_files_per_iteration in settings.yaml."
        )

    # ── Read all files ────────────────────────────────────────────────────────
    file_contents: dict[str, str] = {}
    missing: list[str] = []
    for rel_path in plan.files:
        abs_path = project_path / rel_path
        if abs_path.exists():
            file_contents[rel_path] = abs_path.read_text(encoding="utf-8", errors="replace")
        else:
            missing.append(rel_path)

    # ── Build user prompt ─────────────────────────────────────────────────────
    parts: list[str] = [
        f"Task: {plan.task}",
        "",
        "Acceptance criteria:",
        *[f"  - {c}" for c in plan.acceptance_criteria],
        "",
        "Risk points:",
        *[f"  - r" for r in plan.risk_points],
        "",
        f"Allowed files: {', '.join(plan.files)}",
    ]

    if missing:
        parts += ["", f"WARNING — these files were not found on disk: {', '.join(missing)}",
                  "Create them if the task requires it (they are new files)."]

    if evaluator_feedback:
        parts += [
            "",
            f"=== EVALUATOR FEEDBACK (iteration {iteration - 1}) ===",
            evaluator_feedback,
            "",
            "Address the above issues in your changes.",
        ]

    parts += ["", "=== FILE CONTENTS ==="]
    for rel_path, content in file_contents.items():
        parts += [
            "",
            f"--- FILE: {rel_path} ---",
            content,
            f"--- END: {rel_path} ---",
        ]
    if missing:
        for rel_path in missing:
            parts += ["", f"--- FILE: {rel_path} --- (does not exist yet — create if needed)"]

    raw = client.chat(system=SYSTEM, user="\n".join(parts), max_tokens=8192)

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    data = json.loads(raw)

    # ── Apply changes to disk + record diffs ──────────────────────────────────
    changes: list[CodeChange] = []
    for item in data.get("changes", []):
        rel_path: str = item["file_path"]
        new_content: str = item["content"]
        rationale: str  = item.get("rationale", "")

        original = file_contents.get(rel_path, "")
        abs_path = project_path / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(new_content, encoding="utf-8")

        changes.append(CodeChange(
            file_path=rel_path,
            original=original,
            modified=new_content,
            rationale=rationale,
        ))

    return CoderOutput(
        changes=changes,
        change_summary=data.get("change_summary", ""),
        iteration=iteration,
    )
