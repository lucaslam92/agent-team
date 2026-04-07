import argparse, json
from pathlib import Path

# v3 §8.3: top-k 上限与设计文档对齐
TOP_K = {"feature": 10, "rule": 20, "capability": 15, "playbook": 5}

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
    """
    v3 §9.1: intake_result 顶层字段为 task_type / affected_platforms /
    completeness / missing_info / status，不含 requirement_brief 层。
    从顶层字段中提取关键词。
    """
    fields = []
    # missing_info 列表（字符串）
    fields += intake.get("missing_info", [])
    # 原始需求文本（由 normalize_source 传入的 normalized_text）
    fields.append(intake.get("normalized_text", ""))
    # task_type 本身也是有效关键词
    fields.append(intake.get("task_type", ""))
    # affected_platforms
    fields += intake.get("affected_platforms", [])

    text = " ".join([x for x in fields if isinstance(x, str)]).lower()
    tokens = []
    for token in text.replace("/", " ").replace("-", " ").split():
        token = token.strip(" ,.:;!?()[]{}\"'")
        if len(token) >= 3:
            tokens.append(token)
    seen = set()
    result = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result[:20]

def extract_domains(intake: dict) -> list:
    """从 intake 的 domains 或 signals 中推断 domain 列表"""
    domains = intake.get("domains", [])
    if domains:
        return [str(d).lower() for d in domains]
    # 若无显式 domains，尝试从 signals 推断
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
        if kw in name: score += 3
        if kw in summary: score += 2
        if kw in tags: score += 2
        if kw in card_domains: score += 2
    for d in domains:
        if d in card_domains: score += 2
    for pl in platforms:
        if pl.lower() in card_platforms: score += 1
    return score

def top_k(cards: list, keywords: list, platforms: list, domains: list, k: int) -> list:
    scored = []
    for c in cards:
        s = score_card(c, keywords, platforms, domains)
        if s > 0:
            scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:k]]

def match_playbooks(playbooks: list, task_type: str, domains: list) -> list:
    """
    v3 §5.5: 根据 task_type 和 domain 匹配 Playbook
    """
    matched = []
    for pb in playbooks:
        pb_task_types = pb.get("task_types", [])
        pb_domains = [str(d).lower() for d in pb.get("domains", [])]
        task_match = not pb_task_types or task_type in pb_task_types
        domain_match = not pb_domains or any(d in pb_domains for d in domains)
        if task_match and domain_match:
            matched.append(pb)
    return matched[:TOP_K["playbook"]]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="intake_result.json 路径")
    p.add_argument("--knowledge-root", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()

    intake = json.loads(Path(a.input).read_text(encoding="utf-8"))
    root = Path(a.knowledge_root)

    # v3 §9.1: 从顶层字段读取，不再读 requirement_brief
    platforms = intake.get("affected_platforms", []) or []
    task_type = intake.get("task_type", "")
    keywords = extract_keywords(intake)
    domains = extract_domains(intake)

    # 加载各类知识卡
    feature_cards = load_cards(str(root / "normalized" / "features"))
    rule_cards = load_cards(str(root / "normalized" / "rules"))
    capability_cards = load_cards(str(root / "normalized" / "capabilities"))
    playbook_cards_all = load_cards(str(root / "normalized" / "playbooks"))

    result = {
        "query": {
            "keywords": keywords,
            "domains": domains,
            "platforms": platforms,
            "task_type": task_type,
        },
        "feature_cards": top_k(feature_cards, keywords, platforms, domains, TOP_K["feature"]),
        "rule_cards": top_k(rule_cards, keywords, platforms, domains, TOP_K["rule"]),
        "capability_cards": top_k(capability_cards, keywords, platforms, domains, TOP_K["capability"]),
        # v3 §5.5: 新增 Playbook 检索
        "playbook_cards": match_playbooks(playbook_cards_all, task_type, domains),
    }

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
