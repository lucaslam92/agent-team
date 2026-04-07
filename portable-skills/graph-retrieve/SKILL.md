---
name: graph-retrieve
description: Retrieve a relevant subgraph from nodes.json and edges.json using seed matching and k-hop expansion. Use when Claude Code or Claude CLI needs graph-based context enrichment for PRD, design, coding, verification, or resolver input, especially when replacing keyword retrieval with graph retrieval.
---

# Graph Retrieve

## Overview

Use this skill to turn a structured query into a bounded subgraph that downstream skills can interpret. Prefer this skill whenever the workflow needs graph-first context instead of direct keyword search over cards.

## Inputs And Outputs

Expected inputs:

- `query.json`
- `nodes.json`
- `edges.json`

Primary output:

- `subgraph.json`

## Query Contract

The bundled script accepts a JSON query with any of these fields:

- `node_ids`
- `terms`
- `keywords`
- `domains`
- `platforms`
- `task_type`
- `text`

Direct `node_ids` matches are treated as the strongest seed signal. Text and metadata fields are used for fallback matching.

## Workflow

1. Build or refresh the graph index first with `graph-builder`.
2. Prepare a query JSON from intake, mission context, or user request.
3. Run the bundled retrieval script with an explicit hop count and node limit.
4. Pass `subgraph.json` to `code-to-knowledge-interpreter` or a graph-aware resolver.

## Run

```bash
python scripts/graph_retrieve.py \
  --query <query_json> \
  --nodes <nodes_json> \
  --edges <edges_json> \
  --hops 2 \
  --max-nodes 80 \
  --output <subgraph_json>
```

Optional relation filter:

```bash
python scripts/graph_retrieve.py \
  --query <query_json> \
  --nodes <nodes_json> \
  --edges <edges_json> \
  --relations calls,depends_on,implements \
  --hops 2 \
  --max-nodes 80 \
  --output <subgraph_json>
```

## Output Contract

`subgraph.json` should contain:

- original query
- selected seed nodes
- expanded nodes
- expanded edges
- per-node score map
- retrieval metadata and warnings

## Guardrails

- Prefer graph traversal over keyword-only ranking.
- Keep output bounded with `--hops` and `--max-nodes`.
- Preserve edge direction in the output even when traversal considers both incoming and outgoing neighbors.
- Record missing seed IDs or unmatched queries as warnings instead of silently hiding them.
