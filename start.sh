#!/usr/bin/env bash
# 启动 QQ Codex Bridge（前台，日志直接输出）
cd "$(dirname "${BASH_SOURCE[0]}")"
exec python3 -m qq_codex_bridge.main
