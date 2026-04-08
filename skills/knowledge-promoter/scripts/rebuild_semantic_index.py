#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[2]


def normalized_card_paths(knowledge_root: Path) -> list[Path]:
    normalized_root = knowledge_root / "normalized"
    if not normalized_root.exists():
        return []
    return sorted(normalized_root.rglob("*.json"))


def relation_targets(card: dict, field: str) -> list[str]:
    targets = []
    for item in card.get(field, []):
        if isinstance(item, dict):
            value = item.get("id") or item.get("target") or item.get("name")
        else:
            value = item
        text = str(value or "").strip()
        if text:
            targets.append(text)
    return targets


def node_type(card: dict) -> str:
    card_type = str(card.get("card_type") or "").lower()
    if card_type in {"feature", "rule", "capability", "playbook", "capacity"}:
        return card_type
    return "concept"


def build_signal(card: dict, source_path: Path) -> dict:
    summary = str(card.get("summary") or card.get("content") or card.get("name") or card.get("id") or "")
    metadata = {
        "card_type": card.get("card_type"),
        "status": card.get("status"),
        "domains": card.get("domains", []),
        "platforms": card.get("platforms", []),
        "relative_path": str(source_path),
    }

    node = {
        "id": str(card.get("id")),
        "type": node_type(card),
        "title": str(card.get("name") or card.get("id") or ""),
        "content": summary,
        "source": str(source_path),
        "metadata": metadata,
    }

    edges = []
    for target in relation_targets(card, "dependencies"):
        edges.append({"source": node["id"], "relation": "depends_on", "target": target})
    for target in relation_targets(card, "supersedes"):
        edges.append({"source": node["id"], "relation": "supersedes", "target": target})
    for target in relation_targets(card, "conflicts_with"):
        edges.append({"source": node["id"], "relation": "conflicts_with", "target": target})
    for target in relation_targets(card, "supports"):
        edges.append({"source": node["id"], "relation": "related_to", "target": target})
    for target in relation_targets(card, "related_to"):
        edges.append({"source": node["id"], "relation": "related_to", "target": target})
    for target in relation_targets(card, "owned_by"):
        edges.append({"source": node["id"], "relation": "owned_by", "target": target})

    return {"nodes": [node], "edges": edges}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge-root", required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    knowledge_root = Path(args.knowledge_root).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else (knowledge_root / "index")
    report_path = Path(args.report).resolve() if args.report else (output_dir / "rebuild_report.json")

    card_paths = normalized_card_paths(knowledge_root)
    build_graph_script = skill_root() / "graph-builder" / "scripts" / "build_graph.py"

    with tempfile.TemporaryDirectory(prefix="semantic-index-") as temp_dir:
        signals_dir = Path(temp_dir) / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)

        written = []
        for path in card_paths:
            card = load_json(path, None)
            if not isinstance(card, dict) or not card.get("id"):
                continue
            signal = build_signal(card, path)
            signal_path = signals_dir / f"{path.stem}.json"
            write_json(signal_path, signal)
            written.append(str(signal_path))

        subprocess.run(
            [
                sys.executable,
                str(build_graph_script),
                "--signals-dir",
                str(signals_dir),
                "--output-dir",
                str(output_dir),
                "--merge-mode",
                "overwrite",
            ],
            check=True,
        )

    write_json(
        report_path,
        {
            "knowledge_root": str(knowledge_root),
            "output_dir": str(output_dir),
            "card_count": len(card_paths),
            "signal_file_count": len(written),
            "signal_files": written,
            "nodes_path": str(output_dir / "nodes.json"),
            "edges_path": str(output_dir / "edges.json"),
            "graph_meta_path": str(output_dir / "graph_meta.json"),
        },
    )


if __name__ == "__main__":
    main()
