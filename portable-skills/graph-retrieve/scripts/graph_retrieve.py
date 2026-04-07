#!/usr/bin/env python3
import argparse
import json
from collections import defaultdict, deque
from pathlib import Path


def load_query(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8").strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"text": raw}


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def query_terms(query: dict) -> list[str]:
    terms = []
    for key in ("terms", "keywords", "domains", "platforms", "node_ids"):
        terms.extend(str(item) for item in ensure_list(query.get(key)))
    if query.get("task_type"):
        terms.append(str(query["task_type"]))
    if query.get("text"):
        terms.extend(str(query["text"]).split())
    seen = set()
    cleaned = []
    for term in terms:
        token = term.strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        cleaned.append(token)
    return cleaned


def score_node(node: dict, query: dict, terms: list[str]) -> int:
    score = 0
    node_id = str(node.get("id", ""))
    haystack = " ".join(
        [
            str(node.get("id", "")),
            str(node.get("title", "")),
            str(node.get("content", "")),
            str(node.get("source", "")),
            json.dumps(node.get("metadata", {}), ensure_ascii=False),
        ]
    ).lower()

    if node_id in {str(item) for item in ensure_list(query.get("node_ids"))}:
        score += 100

    for term in terms:
        if term == node_id.lower():
            score += 50
        if term in haystack:
            score += 8

    return score


def build_adjacency(edges: list[dict], relation_filter: set[str]):
    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    filtered_edges = []

    for edge in edges:
        relation = str(edge.get("relation", ""))
        if relation_filter and relation not in relation_filter:
            continue
        filtered_edges.append(edge)
        outgoing[edge["source"]].append(edge)
        incoming[edge["target"]].append(edge)

    return filtered_edges, outgoing, incoming


def expand(seed_ids: list[str], outgoing, incoming, hops: int) -> tuple[dict, set]:
    distances = {}
    included_edges = set()
    queue = deque()

    for node_id in seed_ids:
        distances[node_id] = 0
        queue.append(node_id)

    while queue:
        current = queue.popleft()
        current_hop = distances[current]
        if current_hop >= hops:
            continue

        neighbors = outgoing.get(current, []) + incoming.get(current, [])
        for edge in neighbors:
            included_edges.add((edge["source"], edge["relation"], edge["target"]))
            neighbor = edge["target"] if edge["source"] == current else edge["source"]
            if neighbor not in distances or distances[neighbor] > current_hop + 1:
                distances[neighbor] = current_hop + 1
                queue.append(neighbor)

    return distances, included_edges


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--nodes", required=True)
    parser.add_argument("--edges", required=True)
    parser.add_argument("--hops", type=int, default=2)
    parser.add_argument("--max-nodes", type=int, default=80)
    parser.add_argument("--relations", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    query = load_query(Path(args.query))
    nodes = json.loads(Path(args.nodes).read_text(encoding="utf-8"))
    edges = json.loads(Path(args.edges).read_text(encoding="utf-8"))
    relation_filter = {item.strip() for item in args.relations.split(",") if item.strip()}
    terms = query_terms(query)

    scored = []
    warnings = []
    for node in nodes:
        score = score_node(node, query, terms)
        if score > 0:
            scored.append((score, node))

    scored.sort(key=lambda item: item[0], reverse=True)
    seed_nodes = [node for _, node in scored[: min(20, max(1, args.max_nodes // 4))]]

    requested_ids = {str(item) for item in ensure_list(query.get("node_ids"))}
    found_seed_ids = {node["id"] for node in seed_nodes}
    for requested_id in sorted(requested_ids - found_seed_ids):
        warnings.append(f"Requested seed node not found: {requested_id}")
    if not seed_nodes:
        warnings.append("No seed nodes matched the query.")

    filtered_edges, outgoing, incoming = build_adjacency(edges, relation_filter)
    distances, included_edge_keys = expand([node["id"] for node in seed_nodes], outgoing, incoming, args.hops)

    base_scores = {node["id"]: score for score, node in scored}
    ranked_nodes = []
    for node in nodes:
        node_id = node["id"]
        if node_id not in distances:
            continue
        total_score = base_scores.get(node_id, 0) + max(args.hops - distances[node_id] + 1, 0) * 10
        ranked_nodes.append((total_score, node))

    ranked_nodes.sort(key=lambda item: item[0], reverse=True)
    expanded_nodes = [node for _, node in ranked_nodes[: args.max_nodes]]
    included_node_ids = {node["id"] for node in expanded_nodes}

    expanded_edges = []
    for edge in filtered_edges:
        key = (edge["source"], edge["relation"], edge["target"])
        if key not in included_edge_keys:
            continue
        if edge["source"] in included_node_ids and edge["target"] in included_node_ids:
            expanded_edges.append(edge)

    output = {
        "query": query,
        "seed_nodes": seed_nodes,
        "expanded_nodes": expanded_nodes,
        "expanded_edges": expanded_edges,
        "scores": {node_id: base_scores.get(node_id, 0) for node_id in included_node_ids},
        "metadata": {
            "hops": args.hops,
            "max_nodes": args.max_nodes,
            "relation_filter": sorted(relation_filter),
            "seed_count": len(seed_nodes),
            "expanded_node_count": len(expanded_nodes),
            "expanded_edge_count": len(expanded_edges),
            "warnings": warnings,
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
