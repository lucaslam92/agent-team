# ADR-002: Standardize Knowbase Schema

## Status

Accepted

## Context

Raw LLM output is not stable enough to serve as a long-lived engineering knowledge base. The system needs reusable, machine-readable, and reviewable semantic objects.

## Decision

Standardize the knowbase around a bounded card model:

- Feature Card
- Rule Card
- Capability Card
- Playbook Card
- Capacity Profile Card

Interpreter output must be normalized into these schemas before dedupe and persistence.

## Consequences

- semantic output remains machine-friendly and versionable
- missions and resolvers can rely on stable field shapes
- interpreter skills must emit candidates, not arbitrary prose
