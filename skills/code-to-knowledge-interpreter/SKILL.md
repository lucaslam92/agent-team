---
name: code-to-knowledge-interpreter
description: Interpret a subgraph or merged engineering signals into Feature, Rule, and Capability cards for the knowbase. Use when Claude Code or Claude CLI needs to convert graph evidence into structured semantic knowledge, infer reusable cards from code and docs, or prepare normalized card candidates before dedupe and persist steps.
---

# Code To Knowledge Interpreter

## Overview

Use this skill to perform the semantic lift from graph evidence to knowbase card candidates. This skill is the bridge between graph retrieval and semantic persistence.

## Inputs

Preferred inputs:

- `subgraph.json`
- Optional existing knowbase cards for comparison
- Optional mission context such as repo, platform, and domain

Minimum input shape:

```json
{
  "signals": {},
  "existing_knowbase": {}
}
```

## Outputs

Produce structured candidates only:

```json
{
  "feature_cards": [],
  "rule_cards": [],
  "capability_cards": []
}
```

Detailed field guidance lives in [references/card-output-schema.md](references/card-output-schema.md). Read it before generating cards when you need exact field shape or evidence conventions.

## Responsibilities

- Merge multi-source evidence from code, docs, APIs, and graph relations
- Infer business Features
- Lift engineering or business Rules
- Consolidate reusable Capabilities
- Attach evidence references and dependency relationships when available

## Boundaries

- Do semantic interpretation here
- Do not do file crawling, graph construction, dedupe, persistence, or index rebuild here
- Hand card candidates to normalize and dedupe steps after interpretation

## Workflow

1. Read the retrieved subgraph and any mission context.
2. Group evidence by feature, rule, and capability themes.
3. Emit card candidates with stable semantics and traceable evidence.
4. Pass the output to normalization and dedupe tooling.

## Run

```bash
python scripts/interpreter.py \
  --subgraph <subgraph.json> \
  --output <card_candidates.json>
```

## Guardrails

- Prefer explicit evidence over speculation.
- When evidence is weak, emit fewer cards with clearer uncertainty rather than broad guesses.
- Keep card output machine-friendly and ready for downstream normalization.
