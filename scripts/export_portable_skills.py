#!/usr/bin/env python3
import json
import shutil
from pathlib import Path


SKILLS = [
    "prd-mission",
    "prd-intake",
    "context-build",
    "platform-review",
    "architect-converge",
    "prd-compile",
    "semantic-gate",
    "graph-builder",
    "graph-retrieve",
    "code-to-knowledge-interpreter",
    "graph-aware-resolver",
    "architecture-sync",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def copy_skill(src: Path, dst: Path):
    if dst.exists() or dst.is_symlink():
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc"),
    )


def main():
    root = repo_root()
    source_root = root / "skills"
    target_root = root / "portable-skills"
    target_root.mkdir(parents=True, exist_ok=True)
    ds_store = target_root / ".DS_Store"
    if ds_store.exists():
        ds_store.unlink()

    exported = []
    for skill_name in SKILLS:
        src = source_root / skill_name
        if not src.exists():
            continue
        dst = target_root / skill_name
        copy_skill(src, dst)
        exported.append(skill_name)

    manifest = {
        "source_root": str(source_root),
        "target_root": str(target_root),
        "skills": exported,
    }
    (target_root / ".bundle-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({"exported": exported, "target_root": str(target_root)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
