import argparse, json
from pathlib import Path

# v3 §8.3 / §7.2: effective_capabilities 上限（与 context enrichment token 阈值对齐）
CAPABILITY_LIMIT = 15

def tokenize_text(value: str) -> list[str]:
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

def load_subgraph(path: str | None) -> dict:
    if not path:
        return {}
    subgraph_path = Path(path)
    if not subgraph_path.exists():
        return {}
    try:
        return json.loads(subgraph_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def build_graph_context(subgraph: dict) -> dict:
    nodes = subgraph.get("expanded_nodes", []) if isinstance(subgraph, dict) else []
    node_ids = set()
    terms = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", "")).strip()
        if node_id:
            node_ids.add(node_id)
            terms.update(tokenize_text(node_id))
        terms.update(tokenize_text(node.get("title", "")))
        terms.update(tokenize_text(node.get("content", "")))
        metadata = node.get("metadata", {})
        if isinstance(metadata, dict):
            for value in metadata.values():
                if isinstance(value, (str, int, float)):
                    terms.update(tokenize_text(value))
    return {"node_ids": node_ids, "terms": terms, "node_count": len(nodes)}

def load_cards(paths: list) -> list:
    cards = []
    for p in paths:
        base = Path(p)
        if not base.exists():
            continue
        for f in base.glob("*.json"):
            try:
                cards.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass
    return cards

def stage_match(card: dict, stage: str) -> bool:
    """
    v3 §7.2: capability 可能有 stage 字段限制其适用阶段。
    若 card 未声明 stage，则视为全阶段适用。
    """
    card_stages = card.get("stage", [])
    if not card_stages:
        return True
    return stage in card_stages

def score_capability(card: dict, platform: str, keywords: list, domains: list, feature_ids: list) -> int:
    score = 0
    supports = card.get("supports", [])
    tags = [str(x).lower() for x in card.get("tags", [])]
    card_domains = [str(x).lower() for x in card.get("domains", [])]
    card_platforms = [str(x).lower() for x in card.get("platforms", [])]
    name = str(card.get("name", "")).lower()
    summary = str(card.get("summary", "")).lower()
    interfaces = " ".join(card.get("interfaces", [])).lower()

    for fid in feature_ids:
        if fid in supports: score += 4
    for d in domains:
        if d.lower() in card_domains: score += 2
    for kw in keywords:
        kw = kw.lower()
        if kw in name or kw in summary or kw in tags or kw in interfaces: score += 2
    if platform and platform != "all" and platform.lower() in card_platforms:
        score += 1
    return score

def score_capability_graph(card: dict, graph_ctx: dict) -> int:
    if not graph_ctx:
        return 0

    node_ids = graph_ctx.get("node_ids", set())
    graph_terms = graph_ctx.get("terms", set())
    score = 0

    capability_id = str(card.get("id", "")).strip()
    if capability_id and capability_id in node_ids:
        score += 10

    for supported in card.get("supports", []):
        if str(supported) in node_ids:
            score += 6

    for token in tokenize_text(card.get("name", "")):
        if token in graph_terms:
            score += 2
    for token in tokenize_text(card.get("summary", "")):
        if token in graph_terms:
            score += 1
    for token in tokenize_text(" ".join(card.get("interfaces", []))):
        if token in graph_terms:
            score += 1
    for tag in card.get("tags", []):
        for token in tokenize_text(tag):
            if token in graph_terms:
                score += 2
    for domain in card.get("domains", []):
        for token in tokenize_text(domain):
            if token in graph_terms:
                score += 2

    return score

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--global-root", required=True)
    p.add_argument("--local-root", required=True)
    p.add_argument("--subgraph", required=False, default=None)
    p.add_argument("--output", required=True)
    a = p.parse_args()

    ctx = json.loads(Path(a.input).read_text(encoding="utf-8"))
    platform = ctx["platform"]
    keywords = ctx.get("keywords", [])
    domains = ctx.get("domains", [])
    feature_ids = ctx.get("feature_ids", [])
    stage = ctx["stage"]
    graph_ctx = build_graph_context(load_subgraph(a.subgraph))

    cards = load_cards([
        Path(a.global_root) / "normalized" / "capabilities",
        Path(a.local_root) / "capabilities" / "local",
    ])

    ready_scored = []    # availability=ready
    other_scored = []    # 其他 availability
    filtered = []

    for c in cards:
        # v3 §7.2: stage 过滤（原实现缺失）
        if not stage_match(c, stage):
            filtered.append({"id": c.get("id"), "reason": "stage_mismatch"})
            continue
        s = score_capability(c, platform, keywords, domains, feature_ids) + score_capability_graph(c, graph_ctx)
        if s <= 0:
            filtered.append({"id": c.get("id"), "reason": "low_relevance"})
            continue
        # v3 §7.2: ready 优先——分两组，ready 组排在前面，不靠 +2 分数干扰排名
        if c.get("availability") == "ready":
            ready_scored.append((s, c))
        else:
            other_scored.append((s, c))

    ready_scored.sort(key=lambda x: x[0], reverse=True)
    other_scored.sort(key=lambda x: x[0], reverse=True)

    # ready 优先填充，不足时用 other 补充，总上限 CAPABILITY_LIMIT
    combined = ready_scored + other_scored
    effective = [c for _, c in combined[:CAPABILITY_LIMIT]]

    result = {
        "effective_capabilities": effective,
        "filtered_out_capabilities": filtered[:50],
        "graph_context": {
            "enabled": bool(graph_ctx),
            "node_count": graph_ctx.get("node_count", 0),
        },
    }

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
