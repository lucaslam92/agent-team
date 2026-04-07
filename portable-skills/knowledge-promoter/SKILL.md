---
name: knowledge-promoter
description: Promote generated candidate cards into the normalized knowbase through dedupe, merge, conflict checks, and promotion policy evaluation. Use when Claude Code or Claude CLI needs to turn collected candidates into approved knowledge, merge iteration outcomes into the formal knowbase, or govern what can be promoted after a PRD, design, coding, verification, or PR workflow completes.
---

# Knowledge Promoter

## Overview

Use this skill as the governance path from generated candidate knowledge to the formal normalized knowbase. Trigger it whenever candidate cards need review, dedupe, merge, conflict handling, or promotion after an engineering iteration or a collection run.

This skill is the right entrypoint when the goal is:

- promote candidate cards into approved knowledge
- merge iteration outcomes into the knowbase
- resolve duplicates or conflicting cards
- produce promotion decisions and merge reports

## Match Types

The bundled script distinguishes three promotion relationships:

- `same_as`: merge into an existing canonical card
- `supersedes`: approve a newer card and mark the old card deprecated
- `conflicts_with`: keep the candidate, record the conflict, and avoid silent promotion

It also distinguishes three promotion states:

- `approve`: safe to merge into normalized knowbase
- `review`: keep as candidate and emit a review queue item
- `reject`: keep traceability but mark the candidate rejected

## Read First

Before deciding promotion behavior, read:

- [docs/KNOWBASE_ACCUMULATION_DESIGN_v1.md](../../docs/KNOWBASE_ACCUMULATION_DESIGN_v1.md)

## Inputs

Required inputs:

- `semantic-store/generated/`
- `semantic-store/normalized/`

Recommended governance inputs:

- `semantic-store/state/promotion_state.json`
- `semantic-store/state/dedupe_index.json`
- mission outputs or review artifacts that strengthen evidence

## Outputs

Primary output layer:

```text
semantic-store/normalized/
```

Recommended supporting outputs:

- `generated/merge-reports/`
- `state/promotion_state.json`
- `state/dedupe_index.json`

## Workflow

1. Read candidate cards from `generated/`.
2. Compare them with existing normalized cards.
3. Perform dedupe and conflict detection.
4. Decide whether each candidate should be approved, rejected, superseded, or kept as candidate.
5. Persist approved cards into `normalized/`.
6. Write merge reports and update promotion state.

## Promotion Heuristics

Use stronger evidence for stricter card types:

- `capability`: can auto-promote when code and graph evidence are strong
- `feature`: usually needs requirement evidence plus implementation evidence
- `rule`: prefer configuration, validation, contract, or test evidence over doc-only inference
- `playbook` and `capacity`: default to manual review unless explicitly configured otherwise

## Boundaries

- Do govern promotion and merge decisions here.
- Do not do broad source crawling here.
- Do not silently overwrite normalized cards without a recorded merge decision.
- Do not erase candidate evidence just because a card is rejected.

## Coordination

Use this skill after `knowledge-collector`, or after a completed mission that already produced candidate cards.

When promotion changes the semantic truth materially, refresh graph indexes or downstream indexes as needed.

## Run

Use the bundled script when you want a deterministic promotion pass:

```bash
python scripts/promote_knowledge.py \
  --knowledge-root <company_knowbase_root>
```

Recommended outputs:

- `normalized/`
- `generated/merge-reports/`
- `generated/review-queue/`
- `state/promotion_state.json`
- `state/dedupe_index.json`

To apply human review decisions, pass a structured decision file:

```bash
python scripts/promote_knowledge.py \
  --knowledge-root <company_knowbase_root> \
  --review-decisions <review_decisions.json>
```

## Guardrails

- Preserve evidence and source references in every promotion decision.
- Prefer explicit `same_as`, `supersedes`, or `conflicts_with` relationships over destructive replacement.
- Keep `generated/` and `normalized/` separate even when the same card exists in both states.
- Treat Mission consumption of `generated/` as opt-in, not default behavior.
