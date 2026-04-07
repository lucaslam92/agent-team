#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_step(command: list[str], cwd: Path):
    completed = subprocess.run(command, cwd=cwd)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="目标技能目录，例如 ~/.codex/skills")
    parser.add_argument(
        "--mode",
        choices=["copy", "link"],
        default="copy",
        help="安装模式：copy 复制目录，link 创建软链接",
    )
    parser.add_argument(
        "--bundle-root",
        default=None,
        help="portable-skills 目录路径，默认使用仓库内 portable-skills/",
    )
    args = parser.parse_args()

    root = repo_root()
    python = sys.executable

    export_cmd = [python, str(root / "scripts" / "export_portable_skills.py")]
    install_cmd = [
        python,
        str(root / "scripts" / "install_portable_skills.py"),
        "--target",
        args.target,
        "--mode",
        args.mode,
    ]

    if args.bundle_root:
        install_cmd.extend(["--bundle-root", args.bundle_root])

    run_step(export_cmd, cwd=root)
    run_step(install_cmd, cwd=root)


if __name__ == "__main__":
    main()
