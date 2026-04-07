import argparse, json
from pathlib import Path

# v3 §7.1: effective_rules 上限
EFFECTIVE_RULES_LIMIT = 20

SPECIFICITY_ORDER = {"global": 1, "platform": 2, "repo": 3}

def load_rule_cards(paths: list) -> list:
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

def stage_match(rule: dict, stage: str) -> bool:
    return stage in rule.get("enforcement_stage", [])

def scope_match(rule: dict, platform: str, repo_id: str) -> bool:
    scope = rule.get("scope", {})
    level = scope.get("level", "global")
    if level == "global": return True
    if level == "platform": return scope.get("platform") == platform
    if level == "repo": return scope.get("repo") == repo_id
    return False

def score_rule(rule: dict, platform: str, keywords: list, domains: list, feature_ids: list) -> int:
    score = 0
    applies_to = rule.get("applies_to", [])
    tags = [str(x).lower() for x in rule.get("tags", [])]
    rule_domains = [str(x).lower() for x in rule.get("domains", [])]
    name = str(rule.get("name", "")).lower()
    summary = str(rule.get("summary", "")).lower()
    rule_platforms = [str(x).lower() for x in rule.get("platforms", [])]
    for fid in feature_ids:
        if fid in applies_to: score += 4
    for d in domains:
        if d.lower() in rule_domains: score += 2
    for kw in keywords:
        kw = kw.lower()
        if kw in name or kw in summary or kw in tags: score += 2
    if platform and platform != "all" and platform.lower() in rule_platforms: score += 1
    return score

def specificity(rule: dict) -> int:
    return SPECIFICITY_ORDER.get(rule.get("scope", {}).get("level", "global"), 1)

def same_topic(a: dict, b: dict) -> bool:
    """
    两条规则是否讨论同一主题。
    v3 §7.1: 用 rule_type 相同 + (tags 有交集 OR supersedes 关系) 判断。
    """
    same_type = a.get("rule_type") == b.get("rule_type") and a.get("rule_type") is not None
    tags_overlap = bool(set(a.get("tags", [])) & set(b.get("tags", [])))
    # 显式 supersedes 声明
    a_supersedes_b = b.get("id") in a.get("supersedes", [])
    b_supersedes_a = a.get("id") in b.get("supersedes", [])
    return same_type and (tags_overlap or a_supersedes_b or b_supersedes_a)

def apply_override(candidates: list) -> tuple:
    """
    v3 §7.1 override 逻辑：按 specificity 显式覆盖，不依赖 score 排序副作用。

    修复原实现 bug：原代码按 score 降序遍历，若高分 global rule 先于低分 repo rule
    进入 effective 列表，后续 repo rule 才能触发 override；但若 repo rule score 极低
    且未被 low_relevance 过滤，override 依然可以执行——然而这只是"碰巧"正确。
    正确做法：先收集全部候选，再按 global→platform→repo 顺序显式合并，
    后者（更具体）始终覆盖前者（更宽泛）。
    """
    # 按 specificity 升序排列（global 先处理，repo 最后处理，确保 repo 能覆盖 global）
    ordered = sorted(candidates, key=lambda x: specificity(x[1]))

    effective = []    # list of rule dicts
    override_trace = []

    for _, rule in ordered:
        replaced = False
        for idx, ex in enumerate(effective):
            if same_topic(rule, ex):
                spec_rule = specificity(rule)
                spec_ex = specificity(ex)
                if spec_rule > spec_ex:
                    # 当前规则更具体，覆盖已有规则
                    override_trace.append({
                        "base_rule_id": ex.get("id"),
                        "override_rule_id": rule.get("id"),
                        "reason": "more_specific_scope",
                        "base_level": ex.get("scope", {}).get("level"),
                        "override_level": rule.get("scope", {}).get("level"),
                    })
                    effective[idx] = rule
                    replaced = True
                    break
                elif spec_rule == spec_ex:
                    # 同级规则，保留 score 更高者
                    # score 在 ordered 里未携带，重新计算比较意义不大，保留先入者
                    replaced = True
                    break
                # spec_rule < spec_ex：当前规则更宽泛，不覆盖，跳过
                else:
                    replaced = True
                    break
        if not replaced:
            effective.append(rule)

    return effective, override_trace

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--global-root", required=True)
    p.add_argument("--local-root", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()

    ctx = json.loads(Path(a.input).read_text(encoding="utf-8"))
    stage = ctx["stage"]
    platform = ctx["platform"]
    repo_id = ctx["repo_id"]
    keywords = ctx.get("keywords", [])
    domains = ctx.get("domains", [])
    feature_ids = ctx.get("feature_ids", [])

    rules = load_rule_cards([
        Path(a.global_root) / "normalized" / "rules" / "business",
        Path(a.global_root) / "normalized" / "rules" / "platform",
        Path(a.local_root) / "rules" / "local",
    ])

    candidates = []
    filtered = []

    for r in rules:
        if not stage_match(r, stage):
            filtered.append({"id": r.get("id"), "reason": "stage_mismatch"})
            continue
        if not scope_match(r, platform, repo_id):
            filtered.append({"id": r.get("id"), "reason": "scope_mismatch"})
            continue
        s = score_rule(r, platform, keywords, domains, feature_ids)
        # repo 级别规则不因 score=0 被过滤（可能是强制性规则，无关键词匹配）
        if s <= 0 and specificity(r) < SPECIFICITY_ORDER["repo"]:
            filtered.append({"id": r.get("id"), "reason": "low_relevance"})
            continue
        candidates.append((s, r))

    # v3 §7.1: 按 specificity 显式 override，不依赖 score 排序
    effective, override_trace = apply_override(candidates)

    # 最终按 score 降序排列，截断至上限
    effective_scored = sorted(
        [(score_rule(r, platform, keywords, domains, feature_ids), r) for r in effective],
        key=lambda x: x[0], reverse=True
    )
    effective_final = [r for _, r in effective_scored[:EFFECTIVE_RULES_LIMIT]]

    result = {
        "effective_rules": effective_final,
        "override_trace": override_trace,
        "filtered_out_rules": filtered[:50],
    }

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
