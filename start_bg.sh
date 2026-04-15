#!/usr/bin/env bash
# 启动 QQ Codex Bridge（后台，日志写入 bridge.log）
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
nohup python3 -m qq_codex_bridge.main >> "$DIR/bridge.log" 2>&1 &
PID=$!
echo "$PID" > "$DIR/bridge.pid"
echo "Started PID: $PID"
echo "日志: tail -f $DIR/bridge.log"
