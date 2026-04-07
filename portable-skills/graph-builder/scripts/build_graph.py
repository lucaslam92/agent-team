#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

ALLOWED_RELATIONS = {
    "calls",
    "depends_on",
    "related_to",
    "implements",
    "required_by",
    "conflicts_with",
    "supersedes",
    "owned_by",
}

RELATION_FIELDS = {
    "calls": "calls",
    "depends_on": "depends_on",
    "related_to": "related_to",
    "implements": "implements",
    "required_by": "required_by",
    "conflicts_with": "conflicts_with",
    "supersedes": "supersedes",
    "owned_by": "owned_by",
}


def stable_id(prefix: str, payload: str) -> str:
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_node(raw: dict, source_file: Path) -> dict:
    node_type = str(raw.get("type") or raw.get("kind") or "concept").lower()
    source = str(raw.get("source") or source_file)
    title = raw.get("title") or raw.get("name") or raw.get("symbol") or raw.get("path") or ""
    content = raw.get("content") or raw.get("text") or raw.get("summary") or title
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    node_id = raw.get("id")
    if not node_id:
        identity = json.dumps(
            {
                "source": source,
                "title": title,
                "content": content,
                "path": raw.get("path"),
                "symbol": raw.get("symbol"),
                "type": node_type,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        node_id = stable_id("node", identity)
    return {
        "id": str(node_id),
        "type": node_type,
        "content": str(content or ""),
        "source": source,
        "title": str(title or ""),
        "metadata": metadata,
    }


def normalize_edge(raw: dict) -> dict | None:
    source = raw.get("source")
    relation = raw.get("relation")
    target = raw.get("target")
    if not source or not relation or not target:
        return None
    return {
        "source": str(source),
        "relation": str(relation),
        "target": str(target),
    }


def collect_from_object(obj, source_file: Path, nodes: list, edges: list, warnings: list):
    if isinstance(obj, list):
        for item in obj:
            collect_from_object(item, source_file, nodes, edges, warnings)
        return

    if not isinstance(obj, dict):
        warnings.append(f"{source_file}: unsupported JSON root item {type(obj).__name__}")
        return

    if isinstance(obj.get("nodes"), list):
        for raw_node in obj["nodes"]:
            if isinstance(raw_node, dict):
                nodes.append(normalize_node(raw_node, source_file))
        for raw_edge in ensure_list(obj.get("edges")):
            if isinstance(raw_edge, dict):
                edge = normalize_edge(raw_edge)
                if edge:
                    edges.append(edge)
        return

    node = normalize_node(obj, source_file)
    nodes.append(node)

    for field, relation in RELATION_FIELDS.items():
        for value in ensure_list(obj.get(field)):
            if isinstance(value, dict):
                target = value.get("id") or value.get("target") or value.get("name")
            else:
                target = value
            if not target:
                warnings.append(f"{source_file}: skipped empty target for relation {relation}")
                continue
            edges.append(
                {
                    "source": node["id"],
                    "relation": relation,
                    "target": str(target),
                }
            )


def merge_nodes(existing: list, incoming: list) -> dict:
    merged = {node["id"]: node for node in existing}
    for node in incoming:
        current = merged.get(node["id"], {})
        merged[node["id"]] = {
            **current,
            **node,
            "metadata": {
                **(current.get("metadata") or {}),
                **(node.get("metadata") or {}),
            },
        }
    return merged


def merge_edges(existing: list, incoming: list, warnings: list) -> list:
    deduped = {}
    for edge in existing + incoming:
        if edge["relation"] not in ALLOWED_RELATIONS:
            warnings.append(
                f"Skipped edge with unsupported relation '{edge['relation']}' "
                f"({edge['source']} -> {edge['target']})"
            )
            continue
        key = (edge["source"], edge["relation"], edge["target"])
        deduped[key] = edge
    return list(deduped.values())


def add_placeholder_nodes(node_map: dict, edges: list) -> int:
    created = 0
    for edge in edges:
        for node_id in (edge["source"], edge["target"]):
            if node_id not in node_map:
                node_map[node_id] = {
                    "id": node_id,
                    "type": "concept",
                    "content": "",
                    "source": "__placeholder__",
                    "title": node_id,
                    "metadata": {"placeholder": True},
                }
                created += 1
    return created


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--signals-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--merge-mode", choices=["overwrite", "incremental"], default="overwrite")
    args = parser.parse_args()

    signals_dir = Path(args.signals_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    warnings = []
    loaded_files = []
    incoming_nodes = []
    incoming_edges = []

    for path in sorted(signals_dir.rglob("*.json")):
        loaded_files.append(str(path))
        try:
            collect_from_object(load_json(path), path, incoming_nodes, incoming_edges, warnings)
        except Exception as exc:
            warnings.append(f"{path}: failed to parse ({exc})")

    existing_nodes = []
    existing_edges = []
    if args.merge_mode == "incremental":
        nodes_path = output_dir / "nodes.json"
        edges_path = output_dir / "edges.json"
        if nodes_path.exists():
            existing_nodes = load_json(nodes_path)
        if edges_path.exists():
            existing_edges = load_json(edges_path)

    node_map = merge_nodes(existing_nodes, incoming_nodes)
    edges = merge_edges(existing_edges, incoming_edges, warnings)
    placeholder_count = add_placeholder_nodes(node_map, edges)

    nodes = sorted(node_map.values(), key=lambda node: node["id"])
    edges = sorted(edges, key=lambda edge: (edge["source"], edge["relation"], edge["target"]))

    (output_dir / "nodes.json").write_text(
        json.dumps(nodes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "edges.json").write_text(
        json.dumps(edges, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "graph_meta.json").write_text(
        json.dumps(
            {
                "merge_mode": args.merge_mode,
                "input_files": loaded_files,
                "input_file_count": len(loaded_files),
                "node_count": len(nodes),
                "edge_count": len(edges),
                "placeholder_node_count": placeholder_count,
                "allowed_relations": sorted(ALLOWED_RELATIONS),
                "warnings": warnings,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
