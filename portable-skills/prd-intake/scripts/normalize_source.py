import argparse, json, re
from pathlib import Path

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def detect_signals(title: str, desc: str, metadata: dict) -> dict:
    blob = f"{title}\n{desc}".lower()
    issue_type = (metadata.get("issue_type") or "").lower()
    labels = [str(x).lower() for x in metadata.get("labels", [])]
    return {
        # 修复：使用词边界匹配 "add"，避免 "added"/"address" 等误判
        "likely_feature": (
            issue_type in {"story", "epic", "feature"}
            or "feature" in blob
            or bool(re.search(r"\badd\b", blob))
        ),
        "likely_bug": (
            issue_type == "bug"
            or "bug" in labels
            or bool(re.search(r"\bfix\b", blob))
            or "not working" in blob
        ),
        "likely_tech_improvement": (
            "refactor" in labels
            or "tech-debt" in labels
            or "optimize" in blob
        ),
        "mentions_backend": any(k in blob for k in ["api", "backend", "service", "schema", "db", "database", "endpoint"]),
        "mentions_ui": any(k in blob for k in ["ui", "page", "screen", "dialog", "button", "layout"]),
        "mentions_state_flow": any(k in blob for k in ["login", "auth", "state", "status", "permission", "workflow", "session"]),
        "mentions_multi_platform": any(k in blob for k in ["android", "ios", "web", "mobile"]),
    }

def extract_linked_resources(raw: dict) -> list:
    resources = []
    text_blobs = [raw.get("description", ""), raw.get("body", "")]
    for c in raw.get("comments", []):
        text_blobs.append(c.get("content", "") if isinstance(c, dict) else str(c))
    all_text = "\n".join([x for x in text_blobs if x])
    idx = 1
    patterns = [
        ("figma_design", "figma", r"https?://[^\s]*figma\.com[^\s]*"),
        ("copy_sheet", "gsheet", r"https?://docs\.google\.com/spreadsheets/[^\s]+"),
        ("related_doc", "gdoc", r"https?://docs\.google\.com/document/[^\s]+"),
        ("related_doc", "confluence", r"https?://[^\s]*confluence[^\s]*/(?:wiki|pages)/[^\s]*"),
    ]
    for resource_type, source_type, pattern in patterns:
        for m in re.findall(pattern, all_text):
            resources.append({
                "resource_id": f"res_{idx:03d}",
                "resource_type": resource_type,
                "source_type": source_type,
                "source_ref": m,
                "title": "",
                "description": "",
                "priority": "medium",
                "usage_stage": ["prd"],
                "required": False,
                "status": "discovered",
            })
            idx += 1
    return resources

def merge_with_supplement(base: dict, supplement: dict) -> dict:
    """
    v3 §4.2: human-in-the-loop 补充输入合并逻辑。
    将用户补充的字段合并到原始 normalized_input 中，并递增 _revision。
    supplement 中的字段优先覆盖 base 中的同名字段。
    normalized_text 追加补充内容而非覆盖。
    """
    merged = {**base, **supplement}
    # normalized_text 追加，而非覆盖
    base_text = base.get("normalized_text", "")
    supp_text = supplement.get("normalized_text", "")
    if supp_text and supp_text != base_text:
        merged["normalized_text"] = base_text + "\n\n--- Supplemental Input ---\n" + supp_text
    # 递增 revision
    merged["_revision"] = base.get("_revision", 0) + 1
    return merged

def normalize(raw: dict) -> dict:
    title = clean_text(raw.get("title") or raw.get("summary") or "")
    desc = clean_text(raw.get("description") or raw.get("body") or raw.get("source_ref") or "")
    metadata = raw.get("metadata", {})
    comments = raw.get("comments", [])[:5]

    comment_lines = []
    for c in comments:
        cc = clean_text(c.get("content", "") if isinstance(c, dict) else str(c))
        if cc:
            comment_lines.append(f"- {cc}")

    normalized_text = (
        f"Title: {title}\n\n"
        f"Description:\n{desc}\n\n"
        f"Issue Metadata:\n"
        f"- issue_type: {metadata.get('issue_type', '')}\n"
        f"- labels: {metadata.get('labels', [])}\n"
        f"- components: {metadata.get('components', [])}\n"
        f"- priority: {metadata.get('priority', '')}\n"
        f"- status: {metadata.get('status', '')}\n"
    )
    if comment_lines:
        normalized_text += "\nRelevant Comments:\n" + "\n".join(comment_lines) + "\n"

    return {
        "source_type": raw.get("source_type", "unknown"),
        "source_id": raw.get("source_id", ""),
        "title": title,
        "normalized_text": normalized_text.strip(),
        "metadata": metadata,
        "signals": detect_signals(title, desc, metadata),
        "linked_resources": extract_linked_resources(raw),
        "comments": comments,
        "attachments": raw.get("attachments", []),
        # v3 §4.2: 初始 revision 从 input_ref._revision 继承，若无则为 0
        "_revision": raw.get("_revision", 0),
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    # v3 §4.2: 多轮输入合并——传入上一轮 normalized_input 路径
    p.add_argument("--base", required=False, default=None,
                   help="上一轮 normalized_input.json 路径（human-in-the-loop 补充时使用）")
    a = p.parse_args()

    raw = json.loads(Path(a.input).read_text(encoding="utf-8"))
    result = normalize(raw)

    if a.base:
        base = json.loads(Path(a.base).read_text(encoding="utf-8"))
        result = merge_with_supplement(base, result)

    path = Path(a.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
