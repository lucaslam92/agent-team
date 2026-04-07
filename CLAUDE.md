# CLAUDE.md

## What This Repo Is

- This repository contains an AI software engineering system with mission workflows, reusable skills, long-lived knowledge, and a structured semantic store.

## How To Work Here

- Start from the current mission artifact under `artifacts/`.
- Use repository rules from `knowledge/rules/`.
- Use architecture guidance from `knowledge/architecture/`.
- Treat `semantic-store/` as the structured semantic layer, not as prose documentation.
- Do not expand scope beyond the current mission without explicit instruction.

## Required References

- Business context: `knowledge/business/background.md`
- Architecture: `knowledge/architecture/system_overview.md`
- Rules: `knowledge/rules/`
- System design: `docs/PRD_Mission_Design_v3.md`

## Hard Constraints

- Update contracts when behavior changes.
- Keep outputs structured and machine-readable when possible.
- Map work back to current mission artifacts.
- Stop and report blockers rather than inventing missing business rules.

## Completion Bar

- Relevant checks pass when runnable
- Current artifact is updated
- Risks or blockers are recorded
