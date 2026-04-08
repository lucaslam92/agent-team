#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def tokenize(value: str) -> list[str]:
    text = str(value or "").lower()
    tokens = []
    for token in (
        text.replace("/", " ")
        .replace("-", " ")
        .replace("_", " ")
        .replace(".", " ")
        .split()
    ):
        token = token.strip(" ,.:;!?()[]{}\"'")
        if len(token) >= 3:
            tokens.append(token)
    return tokens


def titleize(identifier: str) -> str:
    parts = [part for part in tokenize(identifier) if part]
    return " ".join(part.capitalize() for part in parts[:6]) or identifier


def infer_domains(tokens: list[str]) -> list[str]:
    known = ["payment", "order", "auth", "notification", "security", "permission", "user"]
    return [domain for domain in known if domain in tokens]


def infer_platforms(tokens: list[str]) -> list[str]:
    known = ["backend", "web", "ios", "android", "frontend"]
    return [platform for platform in known if platform in tokens]


def parse_first_int(text: str, patterns: list[str]) -> int | None:
    lowered = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None
    return None


def parse_first_percent(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text.lower())
    if not match:
        return None
    try:
        return float(match.group(1))
    except Exception:
        return None


def classify_node(node: dict) -> str | None:
    node_id = str(node.get("id", "")).lower()
    node_type = str(node.get("type", "")).lower()
    metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
    semantic_hint = str(metadata.get("semantic_hint", "")).lower()
    doc_subtype = str(metadata.get("doc_subtype", "")).lower()
    source_type = str(metadata.get("source_type", "")).lower()
    text = " ".join(
        [
            node_id,
            str(node.get("title", "")),
            str(node.get("content", "")),
        ]
    ).lower()

    if "capacity" in node_id or "capacity" in node_type or any(term in text for term in ["qps", "rps", "latency", "throughput", "availability", "slo", "sla", "p95", "p99"]):
        return "capacity"
    if semantic_hint in {"tech_stack", "architecture"}:
        return "rule"
    if semantic_hint == "frontend_component":
        return "capability" if source_type == "code" else "rule"
    if node_type == "ui_component":
        return "capability" if source_type == "code" else "rule"
    if doc_subtype in {
        "backend_architecture",
        "web_architecture",
        "android_architecture",
        "ios_architecture",
        "frontend_stack",
        "frontend_component_rules",
        "backend_rules",
        "web_rules",
        "android_rules",
        "ios_rules",
        "api_rules",
        "testing_rules",
    } and node_type in {"doc", "concept", "rule"}:
        return "rule"
    if "feature" in node_id or "feature" in node_type or "user flow" in text:
        return "feature"
    if "rule" in node_id or "rule" in node_type or any(term in text for term in ["must", "should", "forbid", "required", "requirement"]):
        return "rule"
    if (
        "capability" in node_id
        or "service" in node_type
        or any(term in text for term in ["capability", "interface", "queue", "service", "api", "client"])
    ):
        return "capability"
    return None


def summarize(node: dict) -> str:
    content = str(node.get("content", "") or node.get("title", "")).strip()
    if len(content) <= 120:
        return content
    return content[:117].rstrip() + "..."


def build_feature_card(node: dict) -> dict:
    tokens = tokenize(" ".join([node.get("id", ""), node.get("title", ""), node.get("content", "")]))
    return {
        "id": str(node.get("id")),
        "name": str(node.get("title") or titleize(str(node.get("id", "")))),
        "summary": summarize(node),
        "domains": infer_domains(tokens),
        "platforms": infer_platforms(tokens),
        "user_flows": [],
        "dependencies": [],
        "evidence": [{"node_id": node.get("id"), "reason": "feature evidence from graph node"}],
    }


def build_rule_card(node: dict) -> dict:
    tokens = tokenize(" ".join([node.get("id", ""), node.get("title", ""), node.get("content", "")]))
    metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
    semantic_hint = str(metadata.get("semantic_hint", "")).lower()
    doc_subtype = str(metadata.get("doc_subtype", "")).lower()
    tags = sorted(set(tokens[:8] + [value for value in [semantic_hint, doc_subtype] if value]))
    return {
        "id": str(node.get("id")),
        "name": str(node.get("title") or titleize(str(node.get("id", "")))),
        "summary": summarize(node),
        "rule_type": "engineering_rule",
        "domains": infer_domains(tokens),
        "tags": tags,
        "scope": {"level": "global"},
        "enforcement_stage": ["prd", "design", "coding"],
        "evidence": [{"node_id": node.get("id"), "reason": "rule evidence from graph node"}],
    }


def build_capability_card(node: dict) -> dict:
    tokens = tokenize(" ".join([node.get("id", ""), node.get("title", ""), node.get("content", "")]))
    interfaces = []
    if node.get("title"):
        interfaces.append(str(node.get("title")))
    return {
        "id": str(node.get("id")),
        "name": str(node.get("title") or titleize(str(node.get("id", "")))),
        "summary": summarize(node),
        "domains": infer_domains(tokens),
        "platforms": infer_platforms(tokens),
        "interfaces": interfaces,
        "availability": "ready",
        "supports": [],
        "evidence": [{"node_id": node.get("id"), "reason": "capability evidence from graph node"}],
    }


def build_capacity_card(node: dict) -> dict:
    text = " ".join([str(node.get("title", "")), str(node.get("content", ""))])
    tokens = tokenize(" ".join([node.get("id", ""), node.get("title", ""), node.get("content", "")]))
    peak_qps = parse_first_int(text, [r"(\d+)\s*qps", r"(\d+)\s*rps"])
    latency_p95_ms = parse_first_int(text, [r"p95[^0-9]{0,8}(\d+)\s*ms", r"(\d+)\s*ms"])
    availability_slo = parse_first_percent(text)
    return {
        "id": str(node.get("id")),
        "name": str(node.get("title") or titleize(str(node.get("id", "")))),
        "summary": summarize(node),
        "domains": infer_domains(tokens),
        "platforms": infer_platforms(tokens),
        "peak_qps": peak_qps,
        "latency_p95_ms": latency_p95_ms,
        "availability_slo": availability_slo,
        "bottlenecks": [],
        "evidence": [{"node_id": node.get("id"), "reason": "capacity evidence from graph node"}],
    }


def dedupe(cards: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for card in cards:
        card_id = card.get("id")
        if not card_id or card_id in seen:
            continue
        seen.add(card_id)
        result.append(card)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subgraph", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-features", type=int, default=10)
    parser.add_argument("--max-rules", type=int, default=20)
    parser.add_argument("--max-capabilities", type=int, default=15)
    parser.add_argument("--max-capacity", type=int, default=10)
    args = parser.parse_args()

    subgraph = json.loads(Path(args.subgraph).read_text(encoding="utf-8"))
    nodes = subgraph.get("expanded_nodes", [])
    edges = subgraph.get("expanded_edges", [])

    feature_cards = []
    rule_cards = []
    capability_cards = []
    capacity_cards = []

    for node in nodes:
        if not isinstance(node, dict):
            continue
        category = classify_node(node)
        if category == "capacity":
            capacity_cards.append(build_capacity_card(node))
        elif category == "feature":
            feature_cards.append(build_feature_card(node))
        elif category == "rule":
            rule_cards.append(build_rule_card(node))
        elif category == "capability":
            capability_cards.append(build_capability_card(node))

    feature_cards = dedupe(feature_cards)[: args.max_features]
    rule_cards = dedupe(rule_cards)[: args.max_rules]
    capability_cards = dedupe(capability_cards)[: args.max_capabilities]
    capacity_cards = dedupe(capacity_cards)[: args.max_capacity]

    feature_ids = {card["id"] for card in feature_cards}
    capability_map = {card["id"]: card for card in capability_cards}

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        relation = edge.get("relation")
        if relation == "depends_on" and source in feature_ids:
            for card in feature_cards:
                if card["id"] == source and target not in card["dependencies"]:
                    card["dependencies"].append(target)
            if target in capability_map and source not in capability_map[target]["supports"]:
                capability_map[target]["supports"].append(source)
        if relation == "implements" and target in feature_ids and source in capability_map:
            if target not in capability_map[source]["supports"]:
                capability_map[source]["supports"].append(target)

    output = {
        "feature_cards": feature_cards,
        "rule_cards": rule_cards,
        "capability_cards": capability_cards,
        "capacity_cards": capacity_cards,
        "metadata": {
            "source_node_count": len(nodes),
            "source_edge_count": len(edges),
            "feature_count": len(feature_cards),
            "rule_count": len(rule_cards),
            "capability_count": len(capability_cards),
            "capacity_count": len(capacity_cards),
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
