# ADR-003: Introduce Code To Knowledge Interpreter

## Status

Accepted

## Context

Graph retrieval produces relevant structure, but missions cannot directly consume raw nodes and edges. A semantic lift step is needed to convert graph evidence into reusable feature, rule, and capability candidates.

## Decision

Introduce `code-to-knowledge-interpreter` as the semantic bridge between subgraph evidence and knowbase cards.

Its responsibilities are:

- interpret graph evidence
- infer Feature, Rule, and Capability candidates
- attach traceable evidence references

Its non-responsibilities are:

- graph construction
- dedupe
- persistence
- index rebuild

## Consequences

- semantic lifting remains explicit and replaceable
- deterministic processing stays in scripts
- downstream normalize and dedupe steps can operate on stable candidate outputs
