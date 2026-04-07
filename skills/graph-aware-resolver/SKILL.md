---
name: graph-aware-resolver
description: Resolve effective rules and capabilities by combining repo, platform, and global priorities with graph retrieval evidence. Use when Claude Code or Claude CLI needs final effective_rules or effective_capabilities for PRD, design, coding, or verification missions and keyword-only resolver inputs are no longer sufficient.
---

# Graph Aware Resolver

## Overview

Use this skill to turn candidate rules and capabilities into mission-ready effective outputs with graph-aware scoring. Prefer this skill once graph retrieval is enabled and missions need deterministic final resolver outputs.

## Inputs

Expected inputs:

- `subgraph.json`
- resolver context such as stage, repo, platform, domains, and feature IDs
- candidate rule and capability cards from the knowbase

## Outputs

Primary outputs:

- `effective_rules.json`
- `effective_capabilities.json`

## Responsibilities

- Preserve resolver priority rules such as `repo > platform > global`
- Add graph proximity as a scoring signal
- Keep override behavior explicit and traceable
- Produce outputs that remain compatible with downstream mission consumers

## Execution Strategy

Until dedicated scripts are moved into this skill, treat the current resolver scripts as the execution engine:

- `skills/context-build/scripts/resolve_rules.py`
- `skills/context-build/scripts/resolve_capabilities.py`

When graph evidence is available, pass `--subgraph <subgraph.json>` to those scripts so graph proximity becomes part of deterministic ranking.

Use graph evidence to evolve those scripts or replace them with equivalents under this skill without breaking output contracts.

## Guardrails

- Resolver logic stays deterministic.
- Do not move semantic interpretation into the resolver.
- Keep `override_trace` and filtered-out reasons visible for debugging.
