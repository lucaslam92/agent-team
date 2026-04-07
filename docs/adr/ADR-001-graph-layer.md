# ADR-001: Introduce Graph Layer

## Status

Accepted

## Context

Keyword retrieval cannot reliably express dependencies, ownership, implementation chains, or cross-module impact. As the system expands from PRD automation to full software engineering workflows, a structure-first retrieval layer is required.

## Decision

Introduce a Graph Layer between Raw inputs and the Semantic Layer.

The Graph Layer is responsible for:

- converting extracted signals into `nodes.json` and `edges.json`
- maintaining allowed relation types
- supporting graph retrieval via seed matching and k-hop expansion

## Consequences

- missions should prefer graph retrieval over keyword retrieval
- `build_graph.py` and `graph_retrieve.py` become core infrastructure
- downstream semantic interpretation and resolver logic can use graph proximity as a first-class signal
