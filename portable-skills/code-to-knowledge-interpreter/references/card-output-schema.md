# Card Output Schema

Use this reference when emitting card candidates from a subgraph.

## Core Rule

Produce candidates only. Do not dedupe, persist, or rebuild indexes here.

## Feature Card

Recommended shape:

```json
{
  "id": "feature.payment.callback.retry",
  "name": "Payment Callback Retry",
  "summary": "Retry failed payment callbacks with bounded backoff.",
  "domains": ["payment"],
  "platforms": ["backend"],
  "user_flows": [],
  "dependencies": [],
  "evidence": [
    {
      "node_id": "svc.payment.retry",
      "reason": "implements retry workflow"
    }
  ]
}
```

## Rule Card

Recommended shape:

```json
{
  "id": "rule.payment.callback.idempotency",
  "name": "Payment Callback Idempotency",
  "summary": "Callback processing must remain idempotent across retries.",
  "rule_type": "engineering_rule",
  "domains": ["payment"],
  "tags": ["idempotency", "retry"],
  "scope": {
    "level": "platform",
    "platform": "backend"
  },
  "enforcement_stage": ["prd", "design", "coding"],
  "evidence": [
    {
      "node_id": "svc.payment.retry",
      "reason": "retry path depends on repeated delivery"
    }
  ]
}
```

## Capability Card

Recommended shape:

```json
{
  "id": "capability.payment.queue",
  "name": "Payment Queue",
  "summary": "Reusable async queue for payment events and retries.",
  "domains": ["payment"],
  "platforms": ["backend"],
  "interfaces": ["enqueuePaymentEvent", "dequeuePaymentEvent"],
  "availability": "ready",
  "supports": ["feature.payment.callback.retry"],
  "evidence": [
    {
      "node_id": "capability.payment.queue",
      "reason": "queue dependency appears in graph"
    }
  ]
}
```

## Evidence Guidance

- Attach evidence whenever you can map a claim back to graph nodes.
- Prefer explicit node references over narrative explanation.
- Use concise `reason` text that tells downstream tools why the node supports the card.

## Uncertainty Guidance

- When evidence is incomplete, emit fewer cards with clearer summaries.
- Avoid inventing interfaces, rule scopes, or dependencies without graph support.
