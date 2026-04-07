---
name: architecture-sync
description: Keep architecture_state.json, ADRs, and skill boundaries aligned with the actual system implementation. Use when Claude Code or Claude CLI changes graph, semantic, resolver, or mission architecture; adds a new core skill; or needs to update architecture_state.json and ADRs before or alongside implementation work.
---

# Architecture Sync

## Overview

Use this skill to keep architecture documents and implementation in sync as the system evolves. Prefer it whenever architectural behavior changes, not only when writing standalone documentation.

## Responsibilities

- Update `docs/architecture_state.json`
- Update or add ADRs under `docs/adr/`
- Check that core skills, scripts, and mission flow still match the documented architecture
- Surface drift between design documents and actual implementation

## Workflow

1. Identify the architectural change being introduced.
2. Update the single-source-of-truth files first or in the same change.
3. Verify that affected skills and scripts still match those files.
4. Record any intentional deviation as an ADR instead of leaving implicit drift.

## Guardrails

- Do not leave graph-first requirements only in prose if runtime behavior changed.
- Do not introduce new core abilities without deciding whether they belong in an existing skill or a new one.
- Keep documents implementation-facing and concise so Claude Code and Claude CLI can consume them directly.
