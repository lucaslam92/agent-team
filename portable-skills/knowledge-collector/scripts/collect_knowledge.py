#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


TEXT_EXTENSIONS = {
    ".md",
    ".mdx",
    ".txt",
    ".rst",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".java",
    ".kt",
    ".go",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
}

CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".java",
    ".kt",
    ".go",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
}

DOC_EXTENSIONS = {".md", ".mdx", ".txt", ".rst", ".yaml", ".yml"}
API_HINTS = {"openapi", "swagger", "api", "graphql"}
IGNORE_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".venv",
    "company-knowbase",
    "semantic-store",
    "portable-skills",
}
DOMAIN_HINTS = {
    "payment",
    "order",
    "auth",
    "notification",
    "user",
    "security",
    "permission",
    "backend",
    "frontend",
    "android",
    "ios",
    "web",
}
RULE_HINTS = {"must", "should", "required", "forbid", "forbidden", "constraint", "policy"}
CAPABILITY_HINTS = {"service", "client", "api", "capability", "interface", "module", "provider", "gateway"}
HTTP_VERBS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
MISSION_ARTIFACT_PATTERNS = {
    "mission_result",
    "intake_result",
    "context_summary",
    "effective_rules",
    "effective_capabilities",
    "final_prd",
    "review_result",
    "validation_result",
}
PR_METADATA_PATTERNS = {"pull_request", "pr_metadata", "pull-request", "pr-"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def safe_filename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")
    if not slug:
        slug = "item"
    return slug[:80]


def skills_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_command(args: list[str]):
    subprocess.run(args, check=True)


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_file_hash(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 128), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command_output(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return completed.stdout


def tokenize_text(value: str) -> list[str]:
    tokens = []
    for token in re.split(r"[^a-zA-Z0-9]+", str(value or "").lower()):
        if len(token) >= 3:
            tokens.append(token)
    return tokens


def relative_path(path: Path, workspace_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace_root.resolve()))
    except Exception:
        return str(path.resolve())


def infer_source_type(path: Path) -> str:
    if detect_pr_metadata_type(path):
        return "pr_metadata"
    if detect_mission_artifact_type(path):
        return "mission_artifact"
    lower_name = path.name.lower()
    lower_path = str(path).lower()
    if any(hint in lower_name or f"/{hint}/" in lower_path for hint in API_HINTS):
        return "api"
    if path.suffix.lower() in CODE_EXTENSIONS:
        return "code"
    if path.suffix.lower() in DOC_EXTENSIONS:
        return "doc"
    return "concept"


def detect_doc_subtype(path: Path) -> str | None:
    lower_path = str(path).lower()
    if "prd" in lower_path:
        return "prd"
    if "design" in lower_path:
        return "design"
    if "adr" in lower_path:
        return "adr"
    if "readme" in lower_path or "docs/" in lower_path:
        return "doc"
    return None


def detect_mission_artifact_type(path: Path) -> str | None:
    lower_path = str(path).lower()
    if "/artifacts/" not in lower_path and "artifacts/" not in lower_path:
        return None
    for pattern in MISSION_ARTIFACT_PATTERNS:
        if pattern in lower_path:
            return pattern
    return "artifact"


def detect_pr_metadata_type(path: Path) -> str | None:
    lower_path = str(path).lower()
    if any(pattern in lower_path for pattern in PR_METADATA_PATTERNS):
        return "pr_metadata"
    return None


def read_text_preview(path: Path, limit: int) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit].strip()
    except Exception:
        return ""


def iter_source_files(source: Path):
    if source.is_file():
        if source.suffix.lower() in TEXT_EXTENSIONS:
            yield source.resolve()
        return

    for root, dirs, files in os.walk(source):
        dirs[:] = [
            name
            for name in dirs
            if name not in IGNORE_DIRS and not name.startswith(".")
        ]
        root_path = Path(root)
        for filename in files:
            path = root_path / filename
            if path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            if filename.startswith("."):
                continue
            yield path.resolve()


def git_changed_files(workspace_root: Path, git_base: str | None, git_head: str | None) -> set[Path]:
    try:
        if git_base:
            revspec = git_base if not git_head else f"{git_base}..{git_head}"
            output = command_output(["git", "diff", "--name-only", revspec, "--"], workspace_root)
        else:
            output = command_output(["git", "status", "--porcelain", "--untracked-files=all"], workspace_root)
    except Exception:
        return set()

    changed = set()
    for line in output.splitlines():
        text = line.strip()
        if not text:
            continue
        if not git_base and len(text) >= 4:
            rel = text[3:].strip()
        else:
            rel = text
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1].strip()
        path = (workspace_root / rel).resolve()
        if path.is_dir():
            for nested in iter_source_files(path):
                changed.add(nested)
        elif path.exists():
            changed.add(path)
    return changed


def try_load_signal_payload(path: Path):
    if path.suffix.lower() != ".json":
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if isinstance(payload, dict):
        if isinstance(payload.get("nodes"), list):
            return payload
        signal_like_keys = {"id", "type", "content", "source", "calls", "depends_on", "related_to", "implements"}
        if signal_like_keys & set(payload.keys()):
            return payload
    if isinstance(payload, list):
        return payload
    return None


def declared_node_ids(payload) -> list[str]:
    node_ids = []
    if isinstance(payload, dict) and isinstance(payload.get("nodes"), list):
        for node in payload.get("nodes", []):
            if isinstance(node, dict) and node.get("id"):
                node_ids.append(str(node["id"]))
        return node_ids
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and item.get("id"):
                node_ids.append(str(item["id"]))
        return node_ids
    if isinstance(payload, dict) and payload.get("id"):
        node_ids.append(str(payload["id"]))
    return node_ids


def make_node(node_id: str, node_type: str, title: str, content: str, source: Path, metadata: dict | None = None) -> dict:
    return {
        "id": node_id,
        "type": node_type,
        "title": title,
        "content": content,
        "source": str(source.resolve()),
        "metadata": metadata or {},
    }


def make_edge(source: str, relation: str, target: str) -> dict:
    return {"source": source, "relation": relation, "target": target}


def split_markdown_sections(text: str, max_sections: int = 8) -> list[tuple[str, str]]:
    sections = []
    current_title = "Document"
    current_lines = []

    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.lstrip("#").strip() or "Section"
            current_lines = []
            continue
        current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return [(title, content) for title, content in sections if content][:max_sections]


def extract_sentences(text: str, max_items: int = 8) -> list[str]:
    pieces = re.split(r"(?<=[.!?。；;])\s+|\n+", text)
    result = []
    for piece in pieces:
        cleaned = piece.strip()
        if len(cleaned) < 12:
            continue
        result.append(cleaned)
        if len(result) >= max_items:
            break
    return result


def detect_rule_sentences(text: str, max_items: int = 6) -> list[str]:
    result = []
    for sentence in extract_sentences(text, max_items * 2):
        lowered = sentence.lower()
        if any(hint in lowered for hint in RULE_HINTS):
            result.append(sentence)
        if len(result) >= max_items:
            break
    return result


def detect_capability_lines(text: str, max_items: int = 6) -> list[str]:
    result = []
    for line in text.splitlines():
        cleaned = line.strip()
        lowered = cleaned.lower()
        if len(cleaned) < 6:
            continue
        if any(hint in lowered for hint in CAPABILITY_HINTS):
            result.append(cleaned)
        if len(result) >= max_items:
            break
    return result


def classify_doc_section(title: str, content: str, doc_subtype: str | None) -> str:
    lowered = f"{title} {content[:200]}".lower()
    if doc_subtype in {"prd", "design"} and any(token in lowered for token in ["feature", "flow", "story", "scenario", "journey"]):
        return "feature"
    if doc_subtype == "adr" and any(token in lowered for token in ["decision", "constraint", "policy"]):
        return "rule"
    if any(token in lowered for token in RULE_HINTS):
        return "rule"
    if any(token in lowered for token in CAPABILITY_HINTS):
        return "service"
    return "doc"


def build_generic_signal(path: Path, workspace_root: Path, file_hash: str, preview_limit: int) -> tuple[dict, list[str]]:
    rel_path = relative_path(path, workspace_root)
    source_type = infer_source_type(path)
    doc_subtype = detect_doc_subtype(path)
    preview = read_text_preview(path, preview_limit)
    node_id = stable_id("source", rel_path)

    related_to = []
    for token in tokenize_text(f"{rel_path} {preview[:300]}"):
        if token in DOMAIN_HINTS:
            related_to.append(f"concept:{token}")

    payload = {
        "id": node_id,
        "type": source_type,
        "title": rel_path,
        "content": preview,
        "source": str(path.resolve()),
        "related_to": sorted(set(related_to)),
        "metadata": {
            "relative_path": rel_path,
            "extension": path.suffix.lower(),
            "source_type": source_type,
            "doc_subtype": doc_subtype,
            "content_hash": file_hash,
            "size_bytes": path.stat().st_size,
        },
    }
    return payload, [node_id]


def build_doc_signal(path: Path, workspace_root: Path, file_hash: str, preview_limit: int) -> tuple[dict, list[str]]:
    rel_path = relative_path(path, workspace_root)
    doc_subtype = detect_doc_subtype(path)
    preview = read_text_preview(path, preview_limit)
    root_id = stable_id("doc", rel_path)
    base_metadata = {
        "relative_path": rel_path,
        "extension": path.suffix.lower(),
        "source_type": "doc",
        "doc_subtype": doc_subtype,
        "content_hash": file_hash,
        "size_bytes": path.stat().st_size,
    }
    nodes = [make_node(root_id, "doc", rel_path, preview[:400], path, dict(base_metadata))]
    edges = []
    node_ids = [root_id]

    for index, (title, content) in enumerate(split_markdown_sections(preview), start=1):
        node_type = classify_doc_section(title, content, doc_subtype)
        section_id = stable_id("section", f"{rel_path}:{index}:{title}")
        nodes.append(
            make_node(
                section_id,
                node_type,
                title,
                content[:600],
                path,
                {**base_metadata, "section_index": index, "section_title": title},
            )
        )
        edges.append(make_edge(root_id, "related_to", section_id))
        node_ids.append(section_id)

    for index, sentence in enumerate(detect_rule_sentences(preview), start=1):
        rule_id = stable_id("rule", f"{rel_path}:rule:{index}:{sentence[:120]}")
        nodes.append(
            make_node(
                rule_id,
                "rule",
                f"Rule {index}",
                sentence[:500],
                path,
                {**base_metadata, "rule_index": index},
            )
        )
        edges.append(make_edge(root_id, "related_to", rule_id))
        node_ids.append(rule_id)

    for index, line in enumerate(detect_capability_lines(preview), start=1):
        capability_id = stable_id("capability", f"{rel_path}:capability:{index}:{line[:120]}")
        nodes.append(
            make_node(
                capability_id,
                "service",
                line[:80],
                line[:400],
                path,
                {**base_metadata, "capability_index": index},
            )
        )
        edges.append(make_edge(capability_id, "implements", root_id))
        node_ids.append(capability_id)

    for token in tokenize_text(f"{rel_path} {preview[:400]}"):
        if token in DOMAIN_HINTS:
            concept_id = f"concept:{token}"
            edges.append(make_edge(root_id, "related_to", concept_id))

    return {"nodes": nodes, "edges": edges}, node_ids


def extract_code_symbols(text: str, max_items: int = 10) -> list[tuple[str, str]]:
    symbols = []
    patterns = [
        (r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", "class"),
        (r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)", "function"),
        (r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)", "function"),
        (r"^\s*const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=", "symbol"),
        (r"^\s*export\s+(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)", "function"),
    ]
    for line in text.splitlines():
        for pattern, symbol_type in patterns:
            match = re.search(pattern, line)
            if match:
                symbols.append((match.group(1), symbol_type))
                break
        if len(symbols) >= max_items:
            break
    return symbols


def extract_imports(text: str, max_items: int = 12) -> list[str]:
    imports = []
    patterns = [
        r"^\s*import\s+.*?\s+from\s+[\"']([^\"']+)[\"']",
        r"^\s*from\s+([A-Za-z0-9_./-]+)\s+import\s+",
        r"^\s*require\([\"']([^\"']+)[\"']\)",
    ]
    for line in text.splitlines():
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                imports.append(match.group(1))
                break
        if len(imports) >= max_items:
            break
    return imports


def build_code_signal(path: Path, workspace_root: Path, file_hash: str, preview_limit: int) -> tuple[dict, list[str]]:
    rel_path = relative_path(path, workspace_root)
    preview = read_text_preview(path, preview_limit)
    file_id = stable_id("code", rel_path)
    base_metadata = {
        "relative_path": rel_path,
        "extension": path.suffix.lower(),
        "source_type": "code",
        "doc_subtype": None,
        "content_hash": file_hash,
        "size_bytes": path.stat().st_size,
    }
    nodes = [make_node(file_id, "code", rel_path, preview[:400], path, dict(base_metadata))]
    edges = []
    node_ids = [file_id]

    for module_name in extract_imports(preview):
        module_id = stable_id("module", module_name.lower())
        nodes.append(
            make_node(
                module_id,
                "concept",
                module_name,
                module_name,
                path,
                {**base_metadata, "module_name": module_name},
            )
        )
        edges.append(make_edge(file_id, "depends_on", module_id))
        node_ids.append(module_id)

    for symbol_name, symbol_kind in extract_code_symbols(preview):
        lowered = symbol_name.lower()
        node_type = "service" if any(hint in lowered for hint in CAPABILITY_HINTS) else "code"
        symbol_id = stable_id("symbol", f"{rel_path}:{symbol_name}")
        nodes.append(
            make_node(
                symbol_id,
                node_type,
                symbol_name,
                f"{symbol_kind} {symbol_name}",
                path,
                {**base_metadata, "symbol_kind": symbol_kind, "symbol_name": symbol_name},
            )
        )
        edges.append(make_edge(symbol_id, "owned_by", file_id))
        node_ids.append(symbol_id)

    for token in tokenize_text(f"{rel_path} {preview[:400]}"):
        if token in DOMAIN_HINTS:
            edges.append(make_edge(file_id, "related_to", f"concept:{token}"))

    return {"nodes": nodes, "edges": edges}, node_ids


def extract_api_endpoints(text: str, max_items: int = 10) -> list[str]:
    endpoints = []
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        verb_match = re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+([/A-Za-z0-9._{}:-]+)", cleaned, re.IGNORECASE)
        if verb_match:
            endpoints.append(f"{verb_match.group(1).upper()} {verb_match.group(2)}")
        else:
            path_match = re.search(r"(^|[\s\"'])(/[-A-Za-z0-9_./{}:]+)", cleaned)
            if path_match:
                endpoints.append(path_match.group(2))
        if len(endpoints) >= max_items:
            break
    return endpoints


def build_api_signal(path: Path, workspace_root: Path, file_hash: str, preview_limit: int) -> tuple[dict, list[str]]:
    rel_path = relative_path(path, workspace_root)
    preview = read_text_preview(path, preview_limit)
    root_id = stable_id("api", rel_path)
    base_metadata = {
        "relative_path": rel_path,
        "extension": path.suffix.lower(),
        "source_type": "api",
        "doc_subtype": None,
        "content_hash": file_hash,
        "size_bytes": path.stat().st_size,
    }
    nodes = [make_node(root_id, "api", rel_path, preview[:400], path, dict(base_metadata))]
    edges = []
    node_ids = [root_id]

    for index, endpoint in enumerate(extract_api_endpoints(preview), start=1):
        endpoint_id = stable_id("endpoint", f"{rel_path}:{endpoint}")
        nodes.append(
            make_node(
                endpoint_id,
                "api",
                endpoint,
                endpoint,
                path,
                {**base_metadata, "endpoint_index": index},
            )
        )
        edges.append(make_edge(endpoint_id, "implements", root_id))
        node_ids.append(endpoint_id)

    for token in tokenize_text(f"{rel_path} {preview[:400]}"):
        if token in DOMAIN_HINTS:
            edges.append(make_edge(root_id, "related_to", f"concept:{token}"))

    return {"nodes": nodes, "edges": edges}, node_ids


def build_mission_signal(path: Path, workspace_root: Path, file_hash: str, preview_limit: int) -> tuple[dict, list[str]]:
    rel_path = relative_path(path, workspace_root)
    artifact_type = detect_mission_artifact_type(path) or "artifact"
    preview = read_text_preview(path, preview_limit)
    payload = try_load_signal_payload(path)
    if payload is None:
        data = load_json(path, {})
    else:
        data = payload if isinstance(payload, dict) else {}

    root_id = stable_id("artifact", rel_path)
    base_metadata = {
        "relative_path": rel_path,
        "extension": path.suffix.lower(),
        "source_type": "mission_artifact",
        "doc_subtype": artifact_type,
        "content_hash": file_hash,
        "size_bytes": path.stat().st_size,
    }
    nodes = [make_node(root_id, "doc", rel_path, preview[:400], path, dict(base_metadata))]
    edges = []
    node_ids = [root_id]

    summary_parts = []
    for key in ("summary", "task_type", "stage", "platform", "repo_id"):
        value = data.get(key)
        if isinstance(value, (str, int, float)):
            summary_parts.append(f"{key}: {value}")
    if summary_parts:
        summary_id = stable_id("artifact-summary", rel_path)
        nodes.append(
            make_node(
                summary_id,
                "doc",
                f"{artifact_type} summary",
                "\n".join(summary_parts)[:600],
                path,
                {**base_metadata, "artifact_role": "summary"},
            )
        )
        edges.append(make_edge(root_id, "related_to", summary_id))
        node_ids.append(summary_id)

    list_fields = {
        "effective_rules": "rule",
        "effective_capabilities": "service",
        "feature_cards": "feature",
        "rule_cards": "rule",
        "capability_cards": "service",
    }
    for field, node_type in list_fields.items():
        values = data.get(field, [])
        if not isinstance(values, list):
            continue
        for index, item in enumerate(values[:12], start=1):
            if isinstance(item, dict):
                item_id = str(item.get("id") or stable_id(field, f"{rel_path}:{index}"))
                title = str(item.get("name") or item.get("title") or item_id)
                content = str(item.get("summary") or item.get("reason") or title)
            else:
                item_id = stable_id(field, f"{rel_path}:{index}:{item}")
                title = str(item)
                content = str(item)
            nodes.append(
                make_node(
                    item_id,
                    node_type,
                    title[:120],
                    content[:500],
                    path,
                    {**base_metadata, "artifact_field": field, "field_index": index},
                )
            )
            relation = "implements" if node_type == "service" else "related_to"
            edges.append(make_edge(root_id, relation, item_id))
            node_ids.append(item_id)

    return {"nodes": nodes, "edges": edges}, node_ids


def build_pr_metadata_signal(path: Path, workspace_root: Path, file_hash: str, preview_limit: int) -> tuple[dict, list[str]]:
    rel_path = relative_path(path, workspace_root)
    preview = read_text_preview(path, preview_limit)
    data = load_json(path, {})
    if not isinstance(data, dict):
        data = {"body": preview}

    root_id = stable_id("pr", rel_path)
    base_metadata = {
        "relative_path": rel_path,
        "extension": path.suffix.lower(),
        "source_type": "pr_metadata",
        "doc_subtype": "pr_metadata",
        "content_hash": file_hash,
        "size_bytes": path.stat().st_size,
    }
    title = str(data.get("title") or rel_path)
    body = str(data.get("body") or preview)
    nodes = [make_node(root_id, "doc", title[:120], body[:500], path, dict(base_metadata))]
    edges = []
    node_ids = [root_id]

    if title:
        title_id = stable_id("pr-title", f"{rel_path}:{title}")
        title_type = "feature" if "feature" in title.lower() else "doc"
        nodes.append(make_node(title_id, title_type, title[:120], title[:300], path, {**base_metadata, "pr_field": "title"}))
        edges.append(make_edge(root_id, "related_to", title_id))
        node_ids.append(title_id)

    for index, sentence in enumerate(detect_rule_sentences(body), start=1):
        rule_id = stable_id("pr-rule", f"{rel_path}:{index}:{sentence[:120]}")
        nodes.append(make_node(rule_id, "rule", f"PR Rule {index}", sentence[:400], path, {**base_metadata, "pr_field": "body_rule"}))
        edges.append(make_edge(root_id, "related_to", rule_id))
        node_ids.append(rule_id)

    changed_files = data.get("changed_files", [])
    if isinstance(changed_files, list):
        for index, item in enumerate(changed_files[:20], start=1):
            rel = str(item)
            file_node_id = stable_id("pr-file", f"{rel_path}:{rel}")
            file_type = "code" if Path(rel).suffix.lower() in CODE_EXTENSIONS else "doc"
            nodes.append(make_node(file_node_id, file_type, rel[:120], rel[:300], path, {**base_metadata, "pr_field": "changed_files", "field_index": index}))
            edges.append(make_edge(root_id, "related_to", file_node_id))
            node_ids.append(file_node_id)

    labels = data.get("labels", [])
    if isinstance(labels, list):
        for label in labels[:12]:
            for token in tokenize_text(label):
                if token in DOMAIN_HINTS:
                    edges.append(make_edge(root_id, "related_to", f"concept:{token}"))

    return {"nodes": nodes, "edges": edges}, node_ids


def build_git_diff_signal(
    workspace_root: Path,
    git_base: str | None,
    git_head: str | None,
    changed_files: list[dict],
    signal_path: Path,
) -> tuple[dict, list[str]]:
    revspec = "working_tree" if not git_base else (git_base if not git_head else f"{git_base}..{git_head}")
    title = f"git changeset {revspec}"
    root_id = stable_id("changeset", revspec)
    base_metadata = {
        "relative_path": relative_path(signal_path, workspace_root),
        "extension": ".json",
        "source_type": "git_changeset",
        "doc_subtype": "git_diff",
        "content_hash": stable_id("hash", revspec),
        "size_bytes": 0,
    }

    commit_lines = []
    if git_base:
        try:
            commit_lines = [
                line.strip()
                for line in command_output(["git", "log", "--oneline", revspec], workspace_root).splitlines()
                if line.strip()
            ][:12]
        except Exception:
            commit_lines = []

    nodes = [make_node(root_id, "doc", title, "\n".join(commit_lines)[:600], signal_path, dict(base_metadata))]
    edges = []
    node_ids = [root_id]

    for index, item in enumerate(changed_files[:50], start=1):
        rel = str(item.get("relative_path", ""))
        if not rel:
            continue
        file_node_id = stable_id("changed-file", f"{revspec}:{rel}")
        node_type = "code" if Path(rel).suffix.lower() in CODE_EXTENSIONS else "doc"
        nodes.append(make_node(file_node_id, node_type, rel[:120], rel[:300], signal_path, {**base_metadata, "changed_index": index}))
        edges.append(make_edge(root_id, "related_to", file_node_id))
        node_ids.append(file_node_id)

    for index, line in enumerate(commit_lines, start=1):
        commit_node_id = stable_id("commit", f"{revspec}:{line}")
        nodes.append(make_node(commit_node_id, "doc", line[:120], line[:300], signal_path, {**base_metadata, "commit_index": index}))
        edges.append(make_edge(root_id, "related_to", commit_node_id))
        node_ids.append(commit_node_id)

    return {"nodes": nodes, "edges": edges}, node_ids


def build_wrapped_signal(path: Path, workspace_root: Path, file_hash: str, preview_limit: int) -> tuple[dict, list[str]]:
    if detect_pr_metadata_type(path):
        return build_pr_metadata_signal(path, workspace_root, file_hash, preview_limit)
    if detect_mission_artifact_type(path):
        return build_mission_signal(path, workspace_root, file_hash, preview_limit)
    source_type = infer_source_type(path)
    if source_type == "api":
        return build_api_signal(path, workspace_root, file_hash, preview_limit)
    if source_type == "code":
        return build_code_signal(path, workspace_root, file_hash, preview_limit)
    if source_type == "doc":
        return build_doc_signal(path, workspace_root, file_hash, preview_limit)
    return build_generic_signal(path, workspace_root, file_hash, preview_limit)


def build_query(changed_sources: list[dict]) -> dict:
    node_ids = []
    terms = []
    text_parts = []
    for item in changed_sources:
        node_ids.extend(item.get("node_ids", []))
        text_parts.append(item.get("relative_path", ""))
        for token in tokenize_text(item.get("relative_path", "")):
            terms.append(token)
        for token in tokenize_text(item.get("source_type", "")):
            terms.append(token)
        for token in tokenize_text(item.get("doc_subtype", "")):
            terms.append(token)

    seen = set()
    cleaned_terms = []
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        cleaned_terms.append(term)

    return {
        "node_ids": node_ids,
        "terms": cleaned_terms[:50],
        "text": " ".join(part for part in text_parts if part),
    }


def load_subgraph_node_map(subgraph: dict) -> dict:
    result = {}
    for node in subgraph.get("expanded_nodes", []):
        if isinstance(node, dict) and node.get("id"):
            result[str(node["id"])] = node
    return result


def unique_dicts(items: list[dict], key_fields: tuple[str, ...]) -> list[dict]:
    seen = set()
    result = []
    for item in items:
        key = tuple(item.get(field) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def infer_confidence(card_type: str, source_refs: list[dict], evidence_count: int) -> float:
    base = {
        "feature": 0.68,
        "rule": 0.70,
        "capability": 0.82,
        "playbook": 0.62,
        "capacity": 0.62,
    }.get(card_type, 0.65)

    source_types = {item.get("source_type") for item in source_refs if item.get("source_type")}
    if "code" in source_types:
        base += 0.05
    if {"doc", "prd", "design", "adr"} & source_types:
        base += 0.03
    if "api" in source_types:
        base += 0.04
    base += min(evidence_count, 3) * 0.03
    return round(min(base, 0.95), 2)


def infer_promotion_policy(card_type: str) -> str:
    if card_type == "capability":
        return "auto_promote"
    return "manual_review"


def enrich_cards(cards: list[dict], card_type: str, subgraph_nodes: dict, changed_sources: list[dict], run_id: str, collected_at: str) -> list[dict]:
    source_by_node = {}
    for node_id, node in subgraph_nodes.items():
        metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        doc_subtype = metadata.get("doc_subtype")
        source_by_node[node_id] = {
            "path": str(node.get("source", "")),
            "relative_path": metadata.get("relative_path") or str(node.get("source", "")),
            "source_type": doc_subtype or metadata.get("source_type") or str(node.get("type", "")),
            "content_hash": metadata.get("content_hash"),
        }

    fallback_refs = [
        {
            "path": item.get("path"),
            "relative_path": item.get("relative_path"),
            "source_type": item.get("doc_subtype") or item.get("source_type"),
            "content_hash": item.get("content_hash"),
        }
        for item in changed_sources[:5]
    ]

    enriched = []
    for card in cards:
        card_copy = dict(card)
        evidence = card_copy.get("evidence", [])
        source_refs = []
        for evidence_item in evidence:
            if not isinstance(evidence_item, dict):
                continue
            node_id = str(evidence_item.get("node_id", "")).strip()
            if node_id and node_id in source_by_node:
                source_refs.append(source_by_node[node_id])
        if not source_refs:
            source_refs = list(fallback_refs)
        source_refs = unique_dicts(source_refs, ("path", "relative_path", "source_type", "content_hash"))

        card_copy["card_type"] = card_type
        card_copy["status"] = "candidate"
        card_copy["confidence"] = infer_confidence(card_type, source_refs, len(evidence))
        card_copy["source_refs"] = source_refs
        card_copy["derived_from"] = [f"knowledge-collector:{run_id}"]
        card_copy["last_verified_at"] = None
        card_copy["promotion_policy"] = infer_promotion_policy(card_type)
        card_copy["collector_run_id"] = run_id
        card_copy["collected_at"] = collected_at
        enriched.append(card_copy)
    return enriched


def candidate_subdir(card_type: str) -> str:
    return {
        "feature": "features",
        "rule": "rules",
        "capability": "capabilities",
        "playbook": "playbooks",
        "capacity": "capacity",
    }.get(card_type, "misc")


def persist_cards(cards: list[dict], output_root: Path, card_type: str) -> list[str]:
    written = []
    target_dir = output_root / candidate_subdir(card_type)
    target_dir.mkdir(parents=True, exist_ok=True)
    for card in cards:
        card_id = str(card.get("id", "unknown"))
        filename = f"{safe_filename(card_id)}-{hashlib.sha1(card_id.encode('utf-8')).hexdigest()[:8]}.json"
        path = target_dir / filename
        write_json(path, card)
        written.append(str(path))
    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--knowledge-root", required=True)
    parser.add_argument("--source", action="append", required=True, help="可重复传入文件或目录")
    parser.add_argument("--mode", choices=["incremental", "overwrite"], default="incremental")
    parser.add_argument("--git-diff-only", action="store_true", help="仅处理 git 变更文件")
    parser.add_argument("--git-base", default=None, help="git diff base revision")
    parser.add_argument("--git-head", default=None, help="git diff head revision，默认 HEAD")
    parser.add_argument("--pr-metadata", action="append", default=[], help="额外纳入的 PR metadata 文件")
    parser.add_argument("--max-content-chars", type=int, default=2400)
    parser.add_argument("--hops", type=int, default=1)
    parser.add_argument("--max-nodes", type=int, default=80)
    parser.add_argument("--output", default=None, help="collector report 输出路径")
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root).resolve()
    knowledge_root = Path(args.knowledge_root).resolve()
    state_dir = knowledge_root / "state"
    generated_root = knowledge_root / "generated"
    collected_at = now_iso()
    run_id = datetime.now(timezone.utc).strftime("collector-%Y%m%dT%H%M%SZ")
    run_dir = generated_root / "inbox" / run_id
    signals_dir = run_dir / "signals"
    graph_index_dir = knowledge_root / "index"
    candidates_root = generated_root / "candidates"
    registry_path = state_dir / "source_registry.json"
    registry = load_json(registry_path, {"version": "1.0", "sources": {}})

    candidate_report_path = run_dir / "candidate_bundle.json"
    collector_report_path = Path(args.output).resolve() if args.output else run_dir / "collector_report.json"

    source_files = []
    explicit_pr_metadata_files = set()
    for raw_source in args.source:
        source_path = Path(raw_source).expanduser().resolve()
        source_files.extend(iter_source_files(source_path))
    for raw_pr_metadata in args.pr_metadata:
        pr_source = Path(raw_pr_metadata).expanduser().resolve()
        pr_files = list(iter_source_files(pr_source))
        source_files.extend(pr_files)
        explicit_pr_metadata_files.update(pr_files)
    source_files = sorted({path for path in source_files})

    if args.git_diff_only:
        changed_by_git = git_changed_files(workspace_root, args.git_base, args.git_head)
        if changed_by_git:
            source_files = [path for path in source_files if path in changed_by_git or path in explicit_pr_metadata_files]

    changed_sources = []
    scanned_files = []

    for path in source_files:
        file_hash = compute_file_hash(path)
        absolute_path = str(path.resolve())
        rel_path = relative_path(path, workspace_root)
        source_type = infer_source_type(path)
        doc_subtype = detect_doc_subtype(path)
        mission_artifact_type = detect_mission_artifact_type(path)
        previous = registry.get("sources", {}).get(absolute_path)

        scanned_files.append(absolute_path)
        if args.mode == "incremental" and previous and previous.get("content_hash") == file_hash:
            continue

        payload = try_load_signal_payload(path)
        if payload is None:
            payload, node_ids = build_wrapped_signal(path, workspace_root, file_hash, args.max_content_chars)
        else:
            node_ids = declared_node_ids(payload)

        signal_name = f"{safe_filename(rel_path)}-{hashlib.sha1(absolute_path.encode('utf-8')).hexdigest()[:8]}.json"
        signal_path = signals_dir / signal_name
        write_json(signal_path, payload)

        changed_sources.append(
            {
                "path": absolute_path,
                "relative_path": rel_path,
                "signal_path": str(signal_path),
                "source_type": source_type,
                "doc_subtype": doc_subtype,
                "mission_artifact_type": mission_artifact_type,
                "content_hash": file_hash,
                "node_ids": node_ids,
            }
        )

    report = {
        "run_id": run_id,
        "collected_at": collected_at,
        "workspace_root": str(workspace_root),
        "knowledge_root": str(knowledge_root),
        "scanned_file_count": len(scanned_files),
        "changed_file_count": len(changed_sources),
        "changed_sources": changed_sources,
        "candidate_bundle_path": str(candidate_report_path),
        "report_path": str(collector_report_path),
    }

    if not changed_sources:
        report["status"] = "no_changes"
        write_json(candidate_report_path, {"metadata": report, "feature_cards": [], "rule_cards": [], "capability_cards": []})
        write_json(collector_report_path, report)
        return

    if args.git_diff_only or args.git_base:
        git_signal_path = signals_dir / "git-diff-context.json"
        git_payload, git_node_ids = build_git_diff_signal(
            workspace_root,
            args.git_base,
            args.git_head,
            changed_sources,
            git_signal_path,
        )
        write_json(git_signal_path, git_payload)
        changed_sources.append(
            {
                "path": str(git_signal_path),
                "relative_path": relative_path(git_signal_path, workspace_root),
                "signal_path": str(git_signal_path),
                "source_type": "git_changeset",
                "doc_subtype": "git_diff",
                "mission_artifact_type": None,
                "content_hash": git_payload["nodes"][0]["metadata"]["content_hash"],
                "node_ids": git_node_ids,
            }
        )
        report["changed_file_count"] = len(changed_sources)

    root = skills_root()
    build_graph_script = root / "graph-builder" / "scripts" / "build_graph.py"
    graph_retrieve_script = root / "graph-retrieve" / "scripts" / "graph_retrieve.py"
    interpreter_script = root / "code-to-knowledge-interpreter" / "scripts" / "interpreter.py"

    run_command(
        [
            sys.executable,
            str(build_graph_script),
            "--signals-dir",
            str(signals_dir),
            "--output-dir",
            str(graph_index_dir),
            "--merge-mode",
            "incremental" if args.mode == "incremental" else "overwrite",
        ]
    )

    query_path = run_dir / "query.json"
    subgraph_path = run_dir / "subgraph.json"
    raw_cards_path = run_dir / "raw_card_candidates.json"

    query = build_query(changed_sources)
    write_json(query_path, query)

    run_command(
        [
            sys.executable,
            str(graph_retrieve_script),
            "--query",
            str(query_path),
            "--nodes",
            str(graph_index_dir / "nodes.json"),
            "--edges",
            str(graph_index_dir / "edges.json"),
            "--hops",
            str(args.hops),
            "--max-nodes",
            str(args.max_nodes),
            "--output",
            str(subgraph_path),
        ]
    )

    run_command(
        [
            sys.executable,
            str(interpreter_script),
            "--subgraph",
            str(subgraph_path),
            "--output",
            str(raw_cards_path),
        ]
    )

    subgraph = load_json(subgraph_path, {})
    raw_cards = load_json(raw_cards_path, {"feature_cards": [], "rule_cards": [], "capability_cards": []})
    subgraph_nodes = load_subgraph_node_map(subgraph)

    feature_cards = enrich_cards(raw_cards.get("feature_cards", []), "feature", subgraph_nodes, changed_sources, run_id, collected_at)
    rule_cards = enrich_cards(raw_cards.get("rule_cards", []), "rule", subgraph_nodes, changed_sources, run_id, collected_at)
    capability_cards = enrich_cards(raw_cards.get("capability_cards", []), "capability", subgraph_nodes, changed_sources, run_id, collected_at)

    written_feature_cards = persist_cards(feature_cards, candidates_root, "feature")
    written_rule_cards = persist_cards(rule_cards, candidates_root, "rule")
    written_capability_cards = persist_cards(capability_cards, candidates_root, "capability")

    candidate_bundle = {
        "metadata": {
            "run_id": run_id,
            "collected_at": collected_at,
            "workspace_root": str(workspace_root),
            "knowledge_root": str(knowledge_root),
            "query_path": str(query_path),
            "subgraph_path": str(subgraph_path),
            "raw_cards_path": str(raw_cards_path),
        },
        "feature_cards": feature_cards,
        "rule_cards": rule_cards,
        "capability_cards": capability_cards,
    }
    write_json(candidate_report_path, candidate_bundle)

    for source in changed_sources:
        registry["sources"][source["path"]] = {
            "relative_path": source["relative_path"],
            "source_type": source["source_type"],
            "doc_subtype": source["doc_subtype"],
            "mission_artifact_type": source["mission_artifact_type"],
            "content_hash": source["content_hash"],
            "last_collected_at": collected_at,
            "run_id": run_id,
            "node_ids": source["node_ids"],
        }
    write_json(registry_path, registry)

    report.update(
        {
            "status": "completed",
            "query_path": str(query_path),
            "subgraph_path": str(subgraph_path),
            "graph_index_dir": str(graph_index_dir),
            "feature_count": len(feature_cards),
            "rule_count": len(rule_cards),
            "capability_count": len(capability_cards),
            "written_candidate_files": written_feature_cards + written_rule_cards + written_capability_cards,
            "registry_path": str(registry_path),
        }
    )
    write_json(collector_report_path, report)


if __name__ == "__main__":
    main()
