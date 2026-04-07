import argparse, json
from pathlib import Path

# v3 §5.8: 与设计文档边类型对齐
# depends_on / conflicts_with / supersedes / related_to / implements / required_by
ALLOWED_RELATIONS = {"depends_on", "conflicts_with", "supersedes", "related_to", "implements", "required_by"}

# v3 §8.3: 扩展后各类型卡片上限，防止 token 爆炸
EXPAND_LIMITS = {"feature": 10, "rule": 20, "capability": 15}

def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def build_card_map(knowledge_root: Path):
    card_map = {}
    for sub in ["features", "rules", "capabilities"]:
        base = knowledge_root / "normalized" / sub
        if not base.exists():
            continue
        for f in base.glob("*.json"):
            try:
                card = json.loads(f.read_text(encoding="utf-8"))
                card_map[card["id"]] = card
            except Exception:
                pass
    return card_map

def dedupe_cards(cards):
    seen = set()
    result = []
    for c in cards:
        cid = c.get("id")
        if cid and cid not in seen:
            seen.add(cid)
            result.append(c)
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--knowledge-root", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()

    candidates = load_json(a.input)
    knowledge_root = Path(a.knowledge_root)
    edges_path = knowledge_root / "index" / "edges.json"
    # v3 §5.8: edges.json 字段为 from / to / type（原实现用 source/target/relation，已修正）
    edges = load_json(str(edges_path)).get("edges", []) if edges_path.exists() else []

    card_map = build_card_map(knowledge_root)

    feature_cards = candidates.get("feature_cards", [])
    rule_cards = candidates.get("rule_cards", [])
    capability_cards = candidates.get("capability_cards", [])

    seed_ids = {
        *(c.get("id") for c in feature_cards),
        *(c.get("id") for c in rule_cards),
        *(c.get("id") for c in capability_cards),
    }
    seed_ids.discard(None)
    expanded_ids = set(seed_ids)

    for edge in edges:
        # 使用 v3 §5.8 定义的字段名：from / to / type
        src = edge.get("from")
        tgt = edge.get("to")
        rel = edge.get("type")
        if src in seed_ids and rel in ALLOWED_RELATIONS and tgt in card_map:
            expanded_ids.add(tgt)

    expanded_cards = [card_map[cid] for cid in expanded_ids if cid in card_map]

    # 按类型分组并应用扩展上限
    all_features = dedupe_cards([c for c in expanded_cards if c.get("card_type") == "feature"])
    all_rules = dedupe_cards([c for c in expanded_cards if c.get("card_type") == "rule"])
    all_capabilities = dedupe_cards([c for c in expanded_cards if c.get("card_type") == "capability"])

    result = {
        "query_trace": {
            "keywords": candidates.get("query", {}).get("keywords", []),
            "seed_ids": sorted(seed_ids),
            "matched_ids": sorted(expanded_ids),
            "expansion_count": len(expanded_ids) - len(seed_ids),
        },
        "feature_cards": all_features[:EXPAND_LIMITS["feature"]],
        "rule_cards": all_rules[:EXPAND_LIMITS["rule"]],
        "capability_cards": all_capabilities[:EXPAND_LIMITS["capability"]],
        "playbook_cards": candidates.get("playbook_cards", []),
    }

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
