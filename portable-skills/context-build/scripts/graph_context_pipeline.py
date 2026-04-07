#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


def skills_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_query(intake: dict) -> dict:
    text = " ".join(
        [
            str(intake.get("summary", "")),
            str(intake.get("task_type", "")),
            " ".join(str(item) for item in intake.get("domains", [])),
            " ".join(str(item) for item in intake.get("affected_platforms", [])),
        ]
    ).strip()
    return {
        "task_type": intake.get("task_type", ""),
        "domains": intake.get("domains", []),
        "platforms": intake.get("affected_platforms", []),
        "keywords": intake.get("domains", []),
        "terms": [token for token in text.split() if token],
        "text": text,
    }


def run_command(args: list[str]):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--intake", required=True)
    parser.add_argument("--nodes", required=True)
    parser.add_argument("--edges", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--hops", type=int, default=2)
    parser.add_argument("--max-nodes", type=int, default=80)
    parser.add_argument("--relations", default="")
    args = parser.parse_args()

    root = skills_root()
    graph_retrieve_script = root / "graph-retrieve" / "scripts" / "graph_retrieve.py"
    interpreter_script = root / "code-to-knowledge-interpreter" / "scripts" / "interpreter.py"

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    intake = json.loads(Path(args.intake).read_text(encoding="utf-8"))
    query = build_query(intake)

    query_path = output_dir / "query.json"
    subgraph_path = output_dir / "subgraph.json"
    card_candidates_path = output_dir / "card_candidates.json"
    context_candidates_path = output_dir / "context_candidates.json"

    query_path.write_text(json.dumps(query, ensure_ascii=False, indent=2), encoding="utf-8")

    run_command(
        [
            sys.executable,
            str(graph_retrieve_script),
            "--query",
            str(query_path),
            "--nodes",
            args.nodes,
            "--edges",
            args.edges,
            "--hops",
            str(args.hops),
            "--max-nodes",
            str(args.max_nodes),
            "--output",
            str(subgraph_path),
        ]
        + (
            ["--relations", args.relations]
            if args.relations.strip()
            else []
        )
    )

    run_command(
        [
            sys.executable,
            str(interpreter_script),
            "--subgraph",
            str(subgraph_path),
            "--output",
            str(card_candidates_path),
        ]
    )

    card_candidates = json.loads(card_candidates_path.read_text(encoding="utf-8"))
    context_candidates = {
        "query": query,
        "feature_cards": card_candidates.get("feature_cards", []),
        "rule_cards": card_candidates.get("rule_cards", []),
        "capability_cards": card_candidates.get("capability_cards", []),
        "playbook_cards": [],
        "metadata": {
            "source": "graph_context_pipeline",
            "subgraph_path": str(subgraph_path),
            "card_candidates_path": str(card_candidates_path),
        },
    }
    context_candidates_path.write_text(
        json.dumps(context_candidates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
