#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

# v3 §8.3: top-k 上限与设计文档对齐
TOP_K = {"feature": 10, "rule": 20, "capability": 15, "playbook": 5}


def skills_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_cards(dir_path: str) -> list:
    base = Path(dir_path)
    if not base.exists():
        return []
    cards = []
    for f in base.glob("*.json"):
        try:
            cards.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cards


def extract_keywords(intake: dict) -> list:
    fields = []
    fields += intake.get("missing_info", [])
    fields.append(intake.get("normalized_text", ""))
    fields.append(intake.get("summary", ""))
    fields.append(intake.get("task_type", ""))
    fields += intake.get("affected_platforms", [])

    text = " ".join([x for x in fields if isinstance(x, str)]).lower()
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
    seen = set()
    result = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            result.append(token)
    return result[:20]


def extract_domains(intake: dict) -> list:
    domains = intake.get("domains", [])
    if domains:
        return [str(d).lower() for d in domains]
    signals = intake.get("signals", {})
    inferred = []
    if signals.get("mentions_backend"):
        inferred.append("backend")
    if signals.get("mentions_ui"):
        inferred.append("frontend")
    if signals.get("mentions_state_flow"):
        inferred.append("auth")
    return inferred


def score_card(card: dict, keywords: list, platforms: list, domains: list) -> int:
    score = 0
    name = str(card.get("name", "")).lower()
    summary = str(card.get("summary", "")).lower()
    tags = [str(x).lower() for x in card.get("tags", [])]
    card_domains = [str(x).lower() for x in card.get("domains", [])]
    card_platforms = [str(x).lower() for x in card.get("platforms", [])]
    for kw in keywords:
        if kw in name:
            score += 3
        if kw in summary:
            score += 2
        if kw in tags:
            score += 2
        if kw in card_domains:
            score += 2
    for domain in domains:
        if domain in card_domains:
            score += 2
    for platform in platforms:
        if platform.lower() in card_platforms:
            score += 1
    return score


def top_k(cards: list, keywords: list, platforms: list, domains: list, k: int) -> list:
    scored = []
    for card in cards:
        score = score_card(card, keywords, platforms, domains)
        if score > 0:
            scored.append((score, card))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [card for _, card in scored[:k]]


def match_playbooks(playbooks: list, task_type: str, domains: list) -> list:
    matched = []
    for playbook in playbooks:
        pb_task_types = playbook.get("task_types", [])
        pb_domains = [str(d).lower() for d in playbook.get("domains", [])]
        task_match = not pb_task_types or task_type in pb_task_types
        domain_match = not pb_domains or any(domain in pb_domains for domain in domains)
        if task_match and domain_match:
            matched.append(playbook)
    return matched[:TOP_K["playbook"]]


def use_graph_pipeline(knowledge_root: Path) -> bool:
    return (knowledge_root / "index" / "nodes.json").exists() and (knowledge_root / "index" / "edges.json").exists()


def run_graph_pipeline(intake_path: Path, knowledge_root: Path, output_path: Path):
    pipeline = skills_root() / "context-build" / "scripts" / "graph_context_pipeline.py"
    output_dir = output_path.parent
    subprocess.run(
        [
            sys.executable,
            str(pipeline),
            "--intake",
            str(intake_path),
            "--nodes",
            str(knowledge_root / "index" / "nodes.json"),
            "--edges",
            str(knowledge_root / "index" / "edges.json"),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def run_legacy_fallback(intake: dict, knowledge_root: Path) -> dict:
    platforms = intake.get("affected_platforms", []) or []
    task_type = intake.get("task_type", "")
    keywords = extract_keywords(intake)
    domains = extract_domains(intake)

    feature_cards = load_cards(str(knowledge_root / "normalized" / "features"))
    rule_cards = load_cards(str(knowledge_root / "normalized" / "rules"))
    capability_cards = load_cards(str(knowledge_root / "normalized" / "capabilities"))

    return {
        "query": {
            "keywords": keywords,
            "domains": domains,
            "platforms": platforms,
            "task_type": task_type,
        },
        "feature_cards": top_k(feature_cards, keywords, platforms, domains, TOP_K["feature"]),
        "rule_cards": top_k(rule_cards, keywords, platforms, domains, TOP_K["rule"]),
        "capability_cards": top_k(capability_cards, keywords, platforms, domains, TOP_K["capability"]),
        "playbook_cards": [],
        "metadata": {
            "source": "legacy_keyword_fallback",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="intake_result.json 路径")
    parser.add_argument("--knowledge-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    intake_path = Path(args.input)
    output_path = Path(args.output)
    knowledge_root = Path(args.knowledge_root)
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    domains = extract_domains(intake)
    task_type = intake.get("task_type", "")
    playbook_cards_all = load_cards(str(knowledge_root / "normalized" / "playbooks"))
    matched_playbooks = match_playbooks(playbook_cards_all, task_type, domains)

    if use_graph_pipeline(knowledge_root):
        result = run_graph_pipeline(intake_path, knowledge_root, output_path)
        metadata = result.get("metadata", {})
        metadata.update(
            {
                "source": "graph_first_wrapper",
                "pipeline": "graph_context_pipeline",
                "fallback_used": False,
            }
        )
        result["metadata"] = metadata
    else:
        result = run_legacy_fallback(intake, knowledge_root)
        metadata = result.get("metadata", {})
        metadata.update(
            {
                "source": "legacy_keyword_fallback",
                "pipeline": "retrieve_knowledge",
                "fallback_used": True,
                "warning": "graph index missing; used legacy keyword retrieval",
            }
        )
        result["metadata"] = metadata

    result["playbook_cards"] = matched_playbooks

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
