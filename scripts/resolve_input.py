import argparse, json, re
from pathlib import Path

JIRA_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9_]+-\d+\b")
GDOC_RE = re.compile(r"docs\.google\.com/document/d/([a-zA-Z0-9-_]+)")
GSHEET_RE = re.compile(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)")
# Confluence URL：支持 /wiki/spaces/ 和 /pages/ 两种路径格式
CONFLUENCE_RE = re.compile(r"https?://[^\s]*confluence[^\s]*/(?:wiki|pages)/[^\s]*")

def resolve_input(value: str, revision: int = 0) -> dict:
    value = value.strip()
    jira_key_match = JIRA_KEY_RE.search(value)

    # Jira: 纯 key（无 http）
    if jira_key_match and "http" not in value:
        return {
            "input_kind": "jira",
            "source_ref": value,
            "source_id": jira_key_match.group(0),
            "_revision": revision,
        }
    # Jira: 完整 URL（支持 /browse/ 及其他路径，只要含 jira key）
    if jira_key_match and ("atlassian.net" in value or "jira" in value.lower()):
        return {
            "input_kind": "jira",
            "source_ref": value,
            "source_id": jira_key_match.group(0),
            "_revision": revision,
        }

    gdoc_match = GDOC_RE.search(value)
    if gdoc_match:
        return {
            "input_kind": "gdoc",
            "source_ref": value,
            "source_id": gdoc_match.group(1),
            "_revision": revision,
        }

    gsheet_match = GSHEET_RE.search(value)
    if gsheet_match:
        return {
            "input_kind": "gsheet",
            "source_ref": value,
            "source_id": gsheet_match.group(1),
            "_revision": revision,
        }

    # Confluence: 优先尝试正则提取完整 URL，source_id 取 URL 本身
    conf_match = CONFLUENCE_RE.search(value)
    if conf_match:
        return {
            "input_kind": "confluence",
            "source_ref": value,
            "source_id": conf_match.group(0),
            "_revision": revision,
        }
    if "confluence" in value.lower():
        return {
            "input_kind": "confluence",
            "source_ref": value,
            "source_id": "",
            "_revision": revision,
        }

    return {
        "input_kind": "raw_text",
        "source_ref": value,
        "source_id": "",
        "_revision": revision,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    # v3 §4.2: human-in-the-loop 多轮输入时传入上一轮的 _revision
    p.add_argument("--revision", type=int, default=0, help="当前输入轮次（human-in-the-loop 补充时递增）")
    a = p.parse_args()

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(resolve_input(a.input, revision=a.revision), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

if __name__ == "__main__":
    main()
