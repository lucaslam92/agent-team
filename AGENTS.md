# AGENTS.md

## Project Mission

- This repository implements an AI-driven software engineering workflow spanning PRD, Design, Coding, Verification, and PR.
- Current default workflow: `PRD -> Design -> Coding -> Verification -> Pro`.

## Read First

- `artifacts/`
- `knowledge/business/background.md`
- `knowledge/architecture/system_overview.md`
- `docs/PRD_Mission_Design_v3.md`

## Mandatory Rules

- Mission artifacts under `artifacts/` are the current task source of truth.
- Long-lived human-readable knowledge lives under `knowledge/`.
- Structured semantic knowledge, indexes, and accumulation state live under `semantic-store/`.
- Do not modify generated artifacts unless the task explicitly requires it.
- Any behavior or contract change must update the corresponding artifact or rule reference.
- Prefer existing architecture and module boundaries over ad hoc expansion.

## Validation Before Completion

- Run the relevant checks for touched modules when runnable.
- Do not mark work complete if acceptance or artifact mapping is missing.
- If a blocker is found, record it in the current mission output instead of guessing.

## Output Expectations

- Prefer structured outputs: `json`, `yaml`, or stable-heading `md`.
- Keep task outputs inside the current mission artifact tree.
- Keep long-lived rules and architecture guidance in `knowledge/`, not in mission reports.
