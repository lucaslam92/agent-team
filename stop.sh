#!/usr/bin/env bash
# 停止后台运行的 QQ Codex Bridge
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/bridge.pid"
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill "$PID" 2>/dev/null; then
        echo "Stopped PID $PID"
    else
        echo "进程 $PID 不存在"
    fi
    rm -f "$PID_FILE"
else
    pkill -f "qq_codex_bridge.main" 2>/dev/null && echo "Stopped" || echo "未找到运行中的进程"
fi
