#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_filename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")
    if not slug:
        slug = "item"
    return slug[:80]


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def tokenize_text(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-zA-Z0-9]+", str(value or "").lower()) if len(token) >= 3]


def dedupe_list(items: list, dict_key_fields: tuple[str, ...] | None = None):
    if dict_key_fields is None:
        seen = set()
        result = []
        for item in items:
            key = json.dumps(item, ensure_ascii=False, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    seen = set()
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = tuple(item.get(field) for field in dict_key_fields)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def card_type_from_path(path: Path) -> str:
    name = path.parent.name
    return {
        "features": "feature",
        "rules": "rule",
        "capabilities": "capability",
        "playbooks": "playbook",
        "capacity": "capacity",
    }.get(name, "unknown")


def load_candidate_cards(candidate_root: Path) -> list[dict]:
    cards = []
    if not candidate_root.exists():
        return cards
    for path in sorted(candidate_root.rglob("*.json")):
        card = load_json(path, None)
        if not isinstance(card, dict):
            continue
        card_type = card.get("card_type") or card_type_from_path(path)
        card["card_type"] = card_type
        card["_candidate_path"] = str(path)
        card["_candidate_mtime"] = path.stat().st_mtime
        cards.append(card)
    return cards


def load_normalized_cards(knowledge_root: Path) -> tuple[dict, dict]:
    normalized_root = knowledge_root / "normalized"
    existing = {}
    name_index = {}
    candidate_paths = [
        normalized_root / "features",
        normalized_root / "capabilities",
        normalized_root / "playbooks",
        normalized_root / "capacity",
        normalized_root / "rules" / "business",
        normalized_root / "rules" / "platform",
        normalized_root / "rules" / "engineering",
    ]
    for base in candidate_paths:
        if not base.exists():
            continue
        for path in sorted(base.glob("*.json")):
            card = load_json(path, None)
            if not isinstance(card, dict) or not card.get("id"):
                continue
            card_type = card.get("card_type")
            if not card_type:
                if "features" in path.parts:
                    card_type = "feature"
                elif "capabilities" in path.parts:
                    card_type = "capability"
                elif "playbooks" in path.parts:
                    card_type = "playbook"
                elif "capacity" in path.parts:
                    card_type = "capacity"
                else:
                    card_type = "rule"
                card["card_type"] = card_type
            key = f"{card_type}:{card['id']}"
            existing[key] = {"card": card, "path": path}
            name_key = build_name_key(card_type, card)
            if name_key:
                name_index[name_key] = {"card": card, "path": path}
    return existing, name_index


def build_name_key(card_type: str, card: dict) -> str | None:
    name = str(card.get("name", "")).strip()
    if not name:
        return None
    tokens = tokenize_text(name)
    if not tokens:
        return None
    return f"{card_type}:{'-'.join(tokens)}"


def iter_existing_by_type(existing_cards: dict, card_type: str) -> list[dict]:
    return [entry for key, entry in existing_cards.items() if key.startswith(f"{card_type}:")]


def source_ref_keys(card: dict) -> set[str]:
    keys = set()
    for item in card.get("source_refs", []):
        if not isinstance(item, dict):
            continue
        if item.get("relative_path"):
            keys.add(f"rel:{item['relative_path']}")
        if item.get("path"):
            keys.add(f"path:{item['path']}")
    return keys


def explicit_relation_ids(card: dict, field: str) -> set[str]:
    values = set()
    for item in card.get(field, []):
        text = str(item).strip()
        if text:
            values.add(text)
    return values


def version_rank(card: dict) -> int:
    text = f"{card.get('id', '')} {card.get('name', '')}"
    matches = re.findall(r"\bv(\d+)\b", text, flags=re.IGNORECASE)
    if not matches:
        return 0
    return max(int(value) for value in matches)


def token_similarity(a: dict, b: dict) -> float:
    tokens_a = set(tokenize_text(f"{a.get('name', '')} {a.get('summary', '')}"))
    tokens_b = set(tokenize_text(f"{b.get('name', '')} {b.get('summary', '')}"))
    if not tokens_a or not tokens_b:
        return 0.0
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def find_canonical_match(candidate: dict, existing_cards: dict, name_index: dict) -> tuple[dict | None, str | None, str | None]:
    card_type = candidate.get("card_type")
    candidate_key = f"{card_type}:{candidate.get('id')}"
    exact = existing_cards.get(candidate_key)
    if exact:
        return exact, "same_as", "exact_id_match"

    for relation_id in explicit_relation_ids(candidate, "supersedes"):
        existing = existing_cards.get(f"{card_type}:{relation_id}")
        if existing:
            return existing, "supersedes", "explicit_supersedes"

    for existing in iter_existing_by_type(existing_cards, card_type):
        existing_id = str(existing["card"].get("id"))
        if existing_id in explicit_relation_ids(candidate, "conflicts_with") or str(candidate.get("id")) in explicit_relation_ids(existing["card"], "conflicts_with"):
            return existing, "conflicts_with", "explicit_conflict"

    name_key = build_name_key(card_type, candidate)
    if name_key and name_key in name_index:
        existing = name_index[name_key]
        if version_rank(candidate) > version_rank(existing["card"]):
            return existing, "supersedes", "higher_version_same_name"
        return existing, "same_as", "same_name_key"

    candidate_sources = source_ref_keys(candidate)
    best_match = None
    best_similarity = 0.0

    for existing in iter_existing_by_type(existing_cards, card_type):
        overlap = candidate_sources & source_ref_keys(existing["card"])
        similarity = token_similarity(candidate, existing["card"])
        if overlap and similarity >= 0.35 and similarity > best_similarity:
            best_match = (existing, "same_as", "shared_source_overlap")
            best_similarity = similarity
        elif similarity >= 0.80 and similarity > best_similarity:
            relation = "supersedes" if version_rank(candidate) > version_rank(existing["card"]) else "same_as"
            reason = "high_semantic_similarity_newer_version" if relation == "supersedes" else "high_semantic_similarity"
            best_match = (existing, relation, reason)
            best_similarity = similarity

    if best_match:
        return best_match
    return None, None, None


def choose_better_card(current: dict, candidate: dict) -> dict:
    current_conf = float(current.get("confidence") or 0)
    candidate_conf = float(candidate.get("confidence") or 0)
    if candidate_conf > current_conf:
        return candidate
    if candidate_conf < current_conf:
        return current
    current_mtime = float(current.get("_candidate_mtime") or 0)
    candidate_mtime = float(candidate.get("_candidate_mtime") or 0)
    return candidate if candidate_mtime >= current_mtime else current


def source_types(card: dict) -> set[str]:
    values = set()
    for item in card.get("source_refs", []):
        if isinstance(item, dict):
            value = item.get("source_type")
            if value:
                values.add(str(value))
    return values


def should_promote(card: dict, auto_threshold: float) -> tuple[bool, str]:
    card_type = card.get("card_type")
    confidence = float(card.get("confidence") or 0)
    evidence_count = len(card.get("evidence", []))
    refs = source_types(card)
    policy = card.get("promotion_policy", "manual_review")

    if card_type == "capability":
        if confidence >= max(0.70, auto_threshold - 0.10) and evidence_count >= 1:
            return True, "capability_auto_promote"
        return False, "capability_evidence_too_weak"

    if policy == "manual_review":
        return False, "manual_review_required"

    if card_type == "feature":
        if confidence >= auto_threshold and evidence_count >= 2 and {"doc", "prd", "design"} & refs and {"code", "api"} & refs:
            return True, "feature_auto_promote"
        return False, "feature_needs_more_evidence"

    if card_type == "rule":
        if confidence >= auto_threshold and evidence_count >= 2 and {"code", "api"} & refs:
            return True, "rule_auto_promote"
        return False, "rule_needs_more_evidence"

    return False, "unsupported_card_type"


def decide_review_state(card: dict, auto_threshold: float, review_threshold: float, reject_threshold: float) -> tuple[str, str]:
    promote, reason = should_promote(card, auto_threshold)
    if promote:
        return "approve", reason

    confidence = float(card.get("confidence") or 0)
    evidence_count = len(card.get("evidence", []))
    card_type = card.get("card_type")

    if confidence < reject_threshold and evidence_count <= 1:
        return "reject", f"{card_type}_below_reject_threshold"
    if confidence >= review_threshold or evidence_count >= 2:
        return "review", reason
    return "reject", reason


def merge_cards(existing: dict | None, candidate: dict, promoted_at: str) -> dict:
    merged = dict(existing or {})
    merged.update({k: v for k, v in candidate.items() if not k.startswith("_")})

    if existing:
        for field in ("domains", "platforms", "tags", "user_flows", "dependencies", "interfaces", "supports", "supersedes", "conflicts_with"):
            merged[field] = dedupe_list(list(existing.get(field, [])) + list(candidate.get(field, [])))
        merged["source_refs"] = dedupe_list(list(existing.get("source_refs", [])) + list(candidate.get("source_refs", [])), ("path", "relative_path", "source_type", "content_hash"))
        merged["evidence"] = dedupe_list(list(existing.get("evidence", [])) + list(candidate.get("evidence", [])), ("node_id", "reason"))
        merged["derived_from"] = dedupe_list(list(existing.get("derived_from", [])) + list(candidate.get("derived_from", [])))
        merged["confidence"] = round(max(float(existing.get("confidence") or 0), float(candidate.get("confidence") or 0)), 2)
    else:
        merged["source_refs"] = dedupe_list(list(candidate.get("source_refs", [])), ("path", "relative_path", "source_type", "content_hash"))
        merged["evidence"] = dedupe_list(list(candidate.get("evidence", [])), ("node_id", "reason"))
        merged["derived_from"] = dedupe_list(list(candidate.get("derived_from", [])))
        merged["confidence"] = round(float(candidate.get("confidence") or 0), 2)

    merged["status"] = "approved"
    merged["last_verified_at"] = promoted_at
    merged["promoted_at"] = promoted_at
    return merged


def mark_superseded(existing: dict, superseding_id: str, promoted_at: str) -> dict:
    updated = dict(existing)
    updated["status"] = "deprecated"
    updated["superseded_by"] = superseding_id
    updated["superseded_at"] = promoted_at
    return updated


def append_relationship(dedupe_index: dict, relationship_type: str, source: str, target: str, updated_at: str, reason: str):
    relationship = {
        "type": relationship_type,
        "source": source,
        "target": target,
        "reason": reason,
        "updated_at": updated_at,
    }
    if relationship not in dedupe_index["relationships"]:
        dedupe_index["relationships"].append(relationship)


def load_review_decisions(path: Path | None) -> dict:
    if not path or not path.exists():
        return {}
    payload = load_json(path, {})
    items = payload.get("items", []) if isinstance(payload, dict) else []
    result = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = item.get("candidate_key")
        if key:
            result[str(key)] = item
            continue
        card_id = item.get("card_id")
        card_type = item.get("card_type")
        if card_id and card_type:
            result[f"{card_type}:{card_id}"] = item
    return result


def apply_review_override(review_decision: dict | None, review_state: str, reason: str) -> tuple[str, str]:
    if not review_decision:
        return review_state, reason
    action = str(review_decision.get("action", "")).strip().lower()
    note = str(review_decision.get("note", "")).strip()
    if action == "approve":
        return "approve", note or "approved_by_review_decision"
    if action == "reject":
        return "reject", note or "rejected_by_review_decision"
    if action in {"keep_candidate", "review"}:
        return "review", note or "kept_in_review_by_decision"
    return review_state, reason


def destination_path(knowledge_root: Path, card: dict) -> Path:
    normalized_root = knowledge_root / "normalized"
    card_type = card.get("card_type")
    card_id = str(card.get("id"))
    filename = f"{safe_filename(card_id)}-{hashlib.sha1(card_id.encode('utf-8')).hexdigest()[:8]}.json"

    if card_type == "feature":
        return normalized_root / "features" / filename
    if card_type == "capability":
        return normalized_root / "capabilities" / filename
    if card_type == "playbook":
        return normalized_root / "playbooks" / filename
    if card_type == "capacity":
        return normalized_root / "capacity" / filename

    rule_type = str(card.get("rule_type", "")).lower()
    scope_level = str(card.get("scope", {}).get("level", "")).lower()
    if scope_level == "platform":
        return normalized_root / "rules" / "platform" / filename
    if rule_type == "business_rule":
        return normalized_root / "rules" / "business" / filename
    return normalized_root / "rules" / "engineering" / filename


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge-root", required=True)
    parser.add_argument("--candidate-root", default=None)
    parser.add_argument("--output", default=None, help="merge report 输出路径")
    parser.add_argument("--auto-promote-threshold", type=float, default=0.85)
    parser.add_argument("--review-threshold", type=float, default=0.70)
    parser.add_argument("--reject-threshold", type=float, default=0.50)
    parser.add_argument("--review-decisions", default=None, help="人工审核决策 JSON")
    args = parser.parse_args()

    knowledge_root = Path(args.knowledge_root).resolve()
    candidate_root = Path(args.candidate_root).resolve() if args.candidate_root else (knowledge_root / "generated" / "candidates")
    state_dir = knowledge_root / "state"
    report_dir = knowledge_root / "generated" / "merge-reports"
    review_queue_dir = knowledge_root / "generated" / "review-queue"
    promoted_at = now_iso()
    run_id = datetime.now(timezone.utc).strftime("promoter-%Y%m%dT%H%M%SZ")
    report_path = Path(args.output).resolve() if args.output else (report_dir / f"{run_id}.json")
    promotion_state_path = state_dir / "promotion_state.json"
    dedupe_index_path = state_dir / "dedupe_index.json"

    raw_candidates = load_candidate_cards(candidate_root)
    deduped_candidates = {}
    for candidate in raw_candidates:
        candidate_key = f"{candidate.get('card_type')}:{candidate.get('id')}"
        if candidate_key not in deduped_candidates:
            deduped_candidates[candidate_key] = candidate
        else:
            deduped_candidates[candidate_key] = choose_better_card(deduped_candidates[candidate_key], candidate)

    existing_cards, name_index = load_normalized_cards(knowledge_root)
    promotion_state = load_json(promotion_state_path, {"version": "1.0", "decisions": {}})
    dedupe_index = load_json(dedupe_index_path, {"version": "1.0", "mappings": {}, "relationships": []})
    review_decisions = load_review_decisions(Path(args.review_decisions).resolve() if args.review_decisions else None)

    decisions = []
    promoted = []
    retained = []
    review_queue = []

    for candidate_key, candidate in sorted(deduped_candidates.items()):
        card_type = candidate.get("card_type")
        card_id = str(candidate.get("id"))
        canonical, match_type, match_reason = find_canonical_match(candidate, existing_cards, name_index)

        review_state, reason = decide_review_state(
            candidate,
            args.auto_promote_threshold,
            args.review_threshold,
            args.reject_threshold,
        )
        review_decision = review_decisions.get(candidate_key)
        review_state, reason = apply_review_override(review_decision, review_state, reason)
        action = "retain_candidate"
        canonical_id = card_id
        target_path = None

        if canonical and match_type == "conflicts_with":
            canonical_id = str(canonical["card"].get("id"))
            action = "queue_conflict_review"
            review_state = "review"
            reason = f"conflict_detected:{match_reason}"
            retained.append({"id": card_id, "reason": reason})
            review_queue.append({"id": card_id, "card_type": card_type, "reason": reason, "candidate_key": candidate_key})
            append_relationship(dedupe_index, "conflicts_with", candidate_key, f"{card_type}:{canonical_id}", promoted_at, match_reason or "conflict")
        elif canonical and match_type == "supersedes":
            canonical_id = str(canonical["card"].get("id"))
            if review_state == "approve":
                superseded_record = mark_superseded(canonical["card"], card_id, promoted_at)
                write_json(canonical["path"], superseded_record)
                merged = merge_cards(None, candidate, promoted_at)
                merged["supersedes"] = dedupe_list(list(merged.get("supersedes", [])) + [canonical_id])
                target_path = destination_path(knowledge_root, merged)
                write_json(target_path, merged)
                existing_cards[f"{card_type}:{card_id}"] = {"card": merged, "path": target_path}
                action = "approve_superseding"
                promoted.append({"id": card_id, "canonical_id": card_id, "path": str(target_path)})
                append_relationship(dedupe_index, "supersedes", candidate_key, f"{card_type}:{canonical_id}", promoted_at, match_reason or "supersedes")
            elif review_state == "review":
                action = "queue_supersedes_review"
                reason = f"supersedes_requires_review:{match_reason}"
                retained.append({"id": card_id, "reason": reason})
                review_queue.append({"id": card_id, "card_type": card_type, "reason": reason, "candidate_key": candidate_key})
                append_relationship(dedupe_index, "supersedes", candidate_key, f"{card_type}:{canonical_id}", promoted_at, match_reason or "supersedes")
            else:
                action = "reject_superseding_candidate"
                reason = f"supersedes_candidate_rejected:{match_reason}"
                retained.append({"id": card_id, "reason": reason})
                append_relationship(dedupe_index, "supersedes", candidate_key, f"{card_type}:{canonical_id}", promoted_at, match_reason or "supersedes")
        elif canonical:
            canonical_id = str(canonical["card"].get("id"))
            approve_existing = review_state == "approve" or canonical["card"].get("status") == "approved"
            if approve_existing:
                merged = merge_cards(canonical["card"], candidate, promoted_at)
                target_path = canonical["path"]
                write_json(target_path, merged)
                existing_cards[f"{card_type}:{canonical_id}"] = {"card": merged, "path": target_path}
                action = "update_existing"
                promoted.append({"id": card_id, "canonical_id": canonical_id, "path": str(target_path)})
                append_relationship(dedupe_index, "same_as", candidate_key, f"{card_type}:{canonical_id}", promoted_at, match_reason or "merge")
            elif review_state == "review":
                action = "queue_merge_review"
                retained.append({"id": card_id, "reason": reason})
                review_queue.append({"id": card_id, "card_type": card_type, "reason": reason, "candidate_key": candidate_key})
            else:
                action = "reject_candidate"
                retained.append({"id": card_id, "reason": reason})
        elif review_state == "approve":
            merged = merge_cards(None, candidate, promoted_at)
            target_path = destination_path(knowledge_root, merged)
            write_json(target_path, merged)
            existing_cards[f"{card_type}:{card_id}"] = {"card": merged, "path": target_path}
            action = "approve_new"
            promoted.append({"id": card_id, "canonical_id": card_id, "path": str(target_path)})
        elif review_state == "review":
            action = "queue_for_review"
            retained.append({"id": card_id, "reason": reason})
            review_queue.append({"id": card_id, "card_type": card_type, "reason": reason, "candidate_key": candidate_key})
        else:
            action = "reject_candidate"
            retained.append({"id": card_id, "reason": reason})

        candidate_path = Path(candidate["_candidate_path"])
        candidate_record = dict(candidate)
        candidate_record.pop("_candidate_mtime", None)
        if action in {"approve_new", "update_existing", "approve_superseding"}:
            candidate_record["status"] = "approved"
        elif action.startswith("reject"):
            candidate_record["status"] = "rejected"
        else:
            candidate_record["status"] = "candidate"
        candidate_record["promotion_status"] = action
        candidate_record["review_state"] = review_state
        candidate_record["last_promotion_at"] = promoted_at
        candidate_record["canonical_id"] = canonical_id
        candidate_record["match_type"] = match_type
        candidate_record["match_reason"] = match_reason
        write_json(candidate_path, candidate_record)

        promotion_state["decisions"][candidate_key] = {
            "card_id": card_id,
            "card_type": card_type,
            "action": action,
            "reason": reason,
            "review_state": review_state,
            "canonical_id": canonical_id,
            "target_path": str(target_path) if target_path else None,
            "updated_at": promoted_at,
            "review_decision": review_decision,
        }
        dedupe_index["mappings"][candidate_key] = f"{card_type}:{canonical_id}"
        decisions.append(
            {
                "candidate_key": candidate_key,
                "card_id": card_id,
                "card_type": card_type,
                "action": action,
                "reason": reason,
                "review_state": review_state,
                "canonical_id": canonical_id,
                "match_type": match_type,
                "match_reason": match_reason,
                "review_decision": review_decision,
                "candidate_path": candidate["_candidate_path"],
                "target_path": str(target_path) if target_path else None,
            }
        )

    write_json(promotion_state_path, promotion_state)
    write_json(dedupe_index_path, dedupe_index)
    review_queue_path = review_queue_dir / f"{run_id}.json"
    write_json(
        review_queue_path,
        {
            "run_id": run_id,
            "promoted_at": promoted_at,
            "knowledge_root": str(knowledge_root),
            "candidate_root": str(candidate_root),
            "queue_count": len(review_queue),
            "items": review_queue,
        },
    )
    write_json(
        report_path,
        {
            "run_id": run_id,
            "promoted_at": promoted_at,
            "knowledge_root": str(knowledge_root),
            "candidate_root": str(candidate_root),
            "candidate_count": len(deduped_candidates),
            "promoted_count": len(promoted),
            "retained_count": len(retained),
            "review_queue_count": len(review_queue),
            "review_decisions_count": len(review_decisions),
            "promoted": promoted,
            "retained": retained,
            "review_queue_path": str(review_queue_path),
            "decisions": decisions,
            "promotion_state_path": str(promotion_state_path),
            "dedupe_index_path": str(dedupe_index_path),
        },
    )


if __name__ == "__main__":
    main()
