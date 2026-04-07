import argparse, json
from pathlib import Path

# v3 §8.3 / §7.2: effective_capabilities 上限（与 context enrichment token 阈值对齐）
CAPABILITY_LIMIT = 15

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

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--global-root", required=True)
    p.add_argument("--local-root", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()

    ctx = json.loads(Path(a.input).read_text(encoding="utf-8"))
    platform = ctx["platform"]
    keywords = ctx.get("keywords", [])
    domains = ctx.get("domains", [])
    feature_ids = ctx.get("feature_ids", [])
    stage = ctx["stage"]

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
        s = score_capability(c, platform, keywords, domains, feature_ids)
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
    }

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
