---
name: graph-builder
description: Build or refresh graph indexes from extracted engineering signals and output nodes.json, edges.json, and graph_meta.json. Use when Claude Code or Claude CLI needs to turn code/doc/api/jira/figma/log signals into a graph layer, rebuild the graph after extraction changes, or prepare graph data for graph retrieval and downstream missions.
---

# Graph Builder

## Overview

Use this skill to convert raw extracted signal files into a deterministic graph index. Prefer this skill whenever a mission needs fresh `nodes.json` and `edges.json` instead of keyword-only context lookup.

## Inputs And Outputs

Expected inputs:

- A directory containing signal JSON files
- Optional existing graph index for incremental merge

Primary outputs:

- `nodes.json`
- `edges.json`
- `graph_meta.json`

Recommended output root:

```text
company-knowbase/index/
```

## Supported Signal Shapes

The bundled script accepts these common shapes:

1. A file containing top-level `nodes` and `edges` arrays
2. A list of node-like objects
3. A single node-like object with relation fields such as `calls`, `depends_on`, `related_to`, `implements`, `required_by`, `conflicts_with`, `supersedes`, or `owned_by`

When an input object has no stable `id`, the script derives one deterministically from the source file and identifying fields.

## Workflow

1. Point the skill at the directory that contains extracted signal JSON files.
2. Choose `overwrite` for a clean rebuild, or `incremental` when merging with an existing graph index.
3. Run the bundled script.
4. Inspect `graph_meta.json` for node counts, edge counts, placeholder nodes, and warnings before handing the graph to `graph-retrieve`.

## Run

```bash
python scripts/build_graph.py \
  --signals-dir <signals_dir> \
  --output-dir <graph_index_dir> \
  --merge-mode overwrite
```

Incremental rebuild:

```bash
python scripts/build_graph.py \
  --signals-dir <signals_dir> \
  --output-dir <graph_index_dir> \
  --merge-mode incremental
```

## Output Contract

`nodes.json` contains normalized graph nodes.

`edges.json` contains normalized graph edges.

`graph_meta.json` contains:

- input file count
- node count
- edge count
- placeholder node count
- warning list
- allowed relation list

## Guardrails

- Keep the graph deterministic. Do not use LLM inference inside this skill.
- Prefer placeholder nodes over silently dropping referenced targets.
- Fail only on malformed top-level input or file write issues. Non-fatal schema mismatches should be recorded as warnings in `graph_meta.json`.
- Treat this skill as the graph construction entrypoint for Claude Code and Claude CLI workflows.
