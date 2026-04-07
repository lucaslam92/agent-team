#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_manifest(bundle_root: Path) -> dict:
    manifest_path = bundle_root / ".bundle-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Bundle manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def remove_path(path: Path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def copy_skill(src: Path, dst: Path):
    if dst.exists() or dst.is_symlink():
        remove_path(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc"),
    )


def link_skill(src: Path, dst: Path):
    if dst.exists() or dst.is_symlink():
        remove_path(dst)
    dst.symlink_to(src.resolve(), target_is_directory=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="目标技能目录，例如 ~/.codex/skills")
    parser.add_argument(
        "--bundle-root",
        default=None,
        help="portable-skills 目录路径，默认使用仓库内 portable-skills/",
    )
    parser.add_argument(
        "--mode",
        choices=["copy", "link"],
        default="copy",
        help="安装模式：copy 复制目录，link 创建软链接",
    )
    args = parser.parse_args()

    root = repo_root()
    bundle_root = Path(args.bundle_root) if args.bundle_root else root / "portable-skills"
    target_root = Path(args.target).expanduser().resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(bundle_root)
    installed = []

    for skill_name in manifest.get("skills", []):
        src = bundle_root / skill_name
        if not src.exists():
            continue
        dst = target_root / skill_name
        if args.mode == "copy":
            copy_skill(src, dst)
        else:
            link_skill(src, dst)
        installed.append(skill_name)

    print(
        json.dumps(
            {
                "bundle_root": str(bundle_root.resolve()),
                "target_root": str(target_root),
                "mode": args.mode,
                "installed": installed,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
