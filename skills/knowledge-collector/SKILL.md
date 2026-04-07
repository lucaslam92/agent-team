---
name: knowledge-collector
description: Collect candidate knowbase cards from code, PRD, design docs, ADRs, APIs, and mission artifacts, then write them into the generated knowbase layer. Use when Claude Code or Claude CLI needs to accumulate knowledge from repo changes, continuously harvest engineering evidence, or prepare graph-backed candidate cards for later promotion into the normalized knowbase.
---

# Knowledge Collector

## Overview

Use this skill as the automatic intake path for knowbase accumulation. Trigger it whenever the workspace has new or changed code, PRD, design docs, ADRs, APIs, or mission artifacts that should be harvested into candidate knowledge.

This skill is the right entrypoint when the goal is:

- collect knowledge continuously
- scan changed engineering inputs
- produce candidate cards, not final approved knowledge
- keep the generated knowbase layer warm for later promotion

## Built-in Source Adapters

The bundled script already applies deterministic adapters before graph build:

- `PRD / Design`: headings, feature sections, rule sentences, capability hints
- `ADR`: decision-oriented sections and rule sentences
- `Code`: files, imports, classes, functions, service-like symbols
- `API`: endpoint-like paths and verb/path pairs
- `Mission Artifacts`: `context_summary`, `effective_rules`, `effective_capabilities`, and similar workflow outputs
- `PR Metadata`: PR title, body, labels, and changed files

Use these adapters first instead of treating every file as a single opaque blob.

## Read First

Before deciding what to collect or where to write outputs, read:

- [docs/KNOWBASE_ACCUMULATION_DESIGN_v1.md](../../docs/KNOWBASE_ACCUMULATION_DESIGN_v1.md)

## Inputs

Typical inputs include:

- changed code directories
- PRD or design documents
- ADRs
- API specifications
- mission outputs such as PRD, review results, validation results, and merged PR artifacts

Recommended state inputs:

- `semantic-store/state/source_registry.json`
- existing `semantic-store/generated/`

## Outputs

Primary output layer:

```text
semantic-store/generated/
```

Recommended outputs:

- `generated/inbox/`
- `generated/candidates/`
- `generated/merge-reports/`

Collector state:

- `state/source_registry.json`

## Workflow

1. Identify changed or newly relevant sources.
2. Extract signals from those sources.
3. Build or refresh graph evidence with `graph-builder`.
4. Retrieve relevant subgraphs when needed with `graph-retrieve`.
5. Convert graph evidence into candidate cards with `code-to-knowledge-interpreter`.
6. Persist only candidate knowledge into `generated/`.
7. Update source scan state so the next run can be incremental.

## Boundaries

- Do collect and standardize candidate knowledge.
- Do not directly promote cards into `normalized/`.
- Do not overwrite approved cards in the formal knowbase.
- Do not treat weak evidence as approved truth.

## Coordination

Prefer using these sibling skills:

- `graph-builder`
- `graph-retrieve`
- `code-to-knowledge-interpreter`

Hand off final approval and promotion to `knowledge-promoter`.

## Run

Use the bundled script when you want a deterministic collection pass:

```bash
python scripts/collect_knowledge.py \
  --workspace-root <workspace_root> \
  --knowledge-root <company_knowbase_root> \
  --source <path_or_dir> \
  --source <path_or_dir>
```

Recommended outputs:

- `generated/inbox/<run_id>/`
- `generated/candidates/`
- `state/source_registry.json`

For incremental engineering collection, prefer git-aware mode:

```bash
python scripts/collect_knowledge.py \
  --workspace-root <workspace_root> \
  --knowledge-root <company_knowbase_root> \
  --source <workspace_root>/docs \
  --source <workspace_root>/src \
  --source <workspace_root>/artifacts \
  --git-diff-only
```

When PR metadata exists outside the changed file set, include it explicitly:

```bash
python scripts/collect_knowledge.py \
  --workspace-root <workspace_root> \
  --knowledge-root <company_knowbase_root> \
  --source <workspace_root>/docs \
  --git-diff-only \
  --pr-metadata <workspace_root>/pr/pull_request.json
```

## Guardrails

- Default to incremental collection, not full rescans, unless the user asks for a rebuild.
- Preserve source references and evidence for every candidate card.
- Prefer fewer, traceable candidates over broad speculative card generation.
- Keep candidate and approved knowledge strictly separated.
