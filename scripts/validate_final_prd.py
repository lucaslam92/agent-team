import argparse, json
from pathlib import Path

# ---------------------------------------------------------------------------
# v3 §10.1: 三层校验
# Layer 1: Schema 合规性（必填字段存在且非空）
# Layer 2: 完整性校验（Playbook required_sections + affected_platforms 覆盖）
# Layer 3: 规则合规性（critical 规则在 PRD 中有体现）
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ["features", "acceptance_criteria", "implementation_hint"]

def layer1_schema(prd: dict) -> list:
    """Layer 1: 必填字段非空检查"""
    issues = []
    for field in REQUIRED_FIELDS:
        val = prd.get(field)
        if not val:
            issues.append({"layer": 1, "type": "missing_required_field", "field": field})
    flow = prd.get("flow", {})
    if not flow.get("user_flow"):
        issues.append({"layer": 1, "type": "missing_required_field", "field": "flow.user_flow"})
    impl_hint = prd.get("implementation_hint", [])
    if not isinstance(impl_hint, list):
        issues.append({"layer": 1, "type": "wrong_type", "field": "implementation_hint", "expected": "list"})
    return issues

def layer2_completeness(prd: dict, context: dict) -> list:
    """
    Layer 2: 完整性校验
    - Playbook required_sections 全部存在于 PRD
    - affected_platforms 中每个平台均有对应实现章节
    """
    issues = []
    prd_sections = set(prd.keys())

    # 2a: Playbook required_sections 检查
    playbooks = context.get("playbook_cards", [])
    for pb in playbooks:
        for section in pb.get("required_sections_in_prd", []):
            if section not in prd_sections:
                issues.append({
                    "layer": 2,
                    "type": "missing_playbook_section",
                    "playbook_id": pb.get("playbook_id", ""),
                    "missing_section": section,
                })

    # 2b: affected_platforms 覆盖检查
    affected_platforms = context.get("affected_platforms", [])
    platform_impl = prd.get("platform_implementation", {})
    for platform in affected_platforms:
        if platform not in platform_impl:
            issues.append({
                "layer": 2,
                "type": "missing_platform_implementation",
                "platform": platform,
                "hint": f"PRD 缺少 platform_implementation.{platform} 章节",
            })

    return issues

def layer3_rule_compliance(prd: dict, context: dict) -> list:
    """
    Layer 3: 规则合规性
    - priority=critical 的 effective_rules 在 PRD 中均有对应体现
    - 检测方式：rule 的 id 或 summary 关键词出现在 PRD 文本中
    """
    issues = []
    effective_rules = context.get("effective_rules", [])
    prd_text = json.dumps(prd, ensure_ascii=False).lower()

    for rule in effective_rules:
        if rule.get("priority") != "critical":
            continue
        rule_id = rule.get("id", "")
        rule_summary = rule.get("summary", "").lower()
        # 用 rule_id 或 summary 中的关键词做宽松匹配
        keywords = [rule_id.lower()] + [w for w in rule_summary.split() if len(w) >= 4]
        matched = any(kw in prd_text for kw in keywords if kw)
        if not matched:
            issues.append({
                "layer": 3,
                "type": "critical_rule_not_reflected",
                "rule_id": rule_id,
                "rule_summary": rule.get("summary", ""),
                "hint": "该 critical 规则未在 PRD 中体现，请补充相关章节或说明",
            })

    return issues

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="final_prd.json 路径")
    p.add_argument("--context", required=False, default=None,
                   help="context_summary.json 路径（含 playbook_cards / effective_rules / affected_platforms）")
    p.add_argument("--output", required=True)
    a = p.parse_args()

    prd = json.loads(Path(a.input).read_text(encoding="utf-8"))
    context = json.loads(Path(a.context).read_text(encoding="utf-8")) if a.context else {}

    l1 = layer1_schema(prd)
    l2 = layer2_completeness(prd, context)
    l3 = layer3_rule_compliance(prd, context)

    all_issues = l1 + l2 + l3
    can_auto_fix = all(i["layer"] == 1 for i in all_issues)  # Layer 1 问题可由 compile 重试修复

    # v3 §4.3: validate 失败时输出 "invalid"（而非 "blocked"），供流程早退出分支使用
    result = {
        "status": "valid" if not all_issues else "invalid",
        "can_auto_fix": can_auto_fix,
        "issue_count": {"layer1": len(l1), "layer2": len(l2), "layer3": len(l3)},
        "issues": all_issues,
    }

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
