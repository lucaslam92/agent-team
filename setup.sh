#!/usr/bin/env bash
# =============================================================================
# QQ Codex Bridge — 一键安装 & 配置引导脚本
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# 颜色 & 输出工具
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
step()    { echo -e "\n${BOLD}${BLUE}━━━ $* ${RESET}"; }
ask()     { echo -en "${YELLOW}?${RESET} $* "; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.yaml"
SERVICE_FILE="/etc/systemd/system/qq-codex-bridge.service"

# ---------------------------------------------------------------------------
# 欢迎界面
# ---------------------------------------------------------------------------
[[ -t 1 ]] && clear   # 只在真实终端清屏
echo -e "${BOLD}${CYAN}"
cat << 'BANNER'
  ___  ___    ___         _            ____         _     _
 / _ \/ _ \  / __|___  __| |_____ __  | __ ) _ _ __| |__ | |
| (_) | (_) | (__/ _ \/ _` / -_) \ /  |  _ \| '_/ _` / _` |/ _ \
 \__\_\\__\_\ \___\___/\__,_\___/_\_\  |____/|_| \__, \__, \___/
                                                   |___/ |___/
BANNER
echo -e "${RESET}"
echo -e "${BOLD}QQ Official Bot × Codex/Claude CLI 转接服务 — 安装向导${RESET}"
echo -e "项目目录: ${SCRIPT_DIR}\n"

# ---------------------------------------------------------------------------
# 步骤 1: 系统环境检查
# ---------------------------------------------------------------------------
step "第 1 步: 检查系统环境"

# Python
if ! command -v python3 &>/dev/null; then
    error "未找到 python3，请先安装 Python 3.10+"
    exit 1
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10 ]]; then
    error "需要 Python 3.10+，当前版本: $PY_VER"
    exit 1
fi
success "Python $PY_VER"

# Node / npm
if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
    warn "未找到 Node.js / npm，尝试自动安装..."
    if command -v apt-get &>/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
        apt-get install -y nodejs
    elif command -v brew &>/dev/null; then
        brew install node
    else
        error "无法自动安装 Node.js，请手动安装后重试: https://nodejs.org"
        exit 1
    fi
fi
NODE_VER=$(node --version)
NPM_VER=$(npm --version)
success "Node.js $NODE_VER  npm $NPM_VER"

# ---------------------------------------------------------------------------
# 步骤 2: 安装 Python 依赖
# ---------------------------------------------------------------------------
step "第 2 步: 安装 Python 依赖"

cd "$SCRIPT_DIR"
pip3 install -q -r requirements.txt
success "Python 依赖安装完成"

# ---------------------------------------------------------------------------
# 步骤 3: 安装 Codex CLI
# ---------------------------------------------------------------------------
step "第 3 步: 安装 Codex CLI"

if command -v codex &>/dev/null; then
    CODEX_VER=$(codex --version 2>/dev/null | head -1 || echo "已安装")
    success "Codex CLI 已存在: $CODEX_VER"
    ask "重新安装? [y/N]"; read -r REINSTALL_CODEX
    if [[ "${REINSTALL_CODEX,,}" == "y" ]]; then
        npm install -g @openai/codex
        success "Codex CLI 更新完成"
    fi
else
    info "安装 Codex CLI (@openai/codex)..."
    npm install -g @openai/codex
    success "Codex CLI 安装完成: $(codex --version 2>/dev/null | head -1)"
fi

CODEX_BIN=$(command -v codex)

# ---------------------------------------------------------------------------
# 步骤 4: 安装 Claude Code CLI
# ---------------------------------------------------------------------------
step "第 4 步: 安装 Claude Code CLI"

if command -v claude &>/dev/null; then
    CLAUDE_VER=$(claude --version 2>/dev/null | head -1 || echo "已安装")
    success "Claude CLI 已存在: $CLAUDE_VER"
    ask "重新安装? [y/N]"; read -r REINSTALL_CLAUDE
    if [[ "${REINSTALL_CLAUDE,,}" == "y" ]]; then
        npm install -g @anthropic-ai/claude-code
        success "Claude CLI 更新完成"
    fi
else
    info "安装 Claude Code CLI (@anthropic-ai/claude-code)..."
    npm install -g @anthropic-ai/claude-code
    success "Claude CLI 安装完成: $(claude --version 2>/dev/null | head -1)"
fi

CLAUDE_BIN=$(command -v claude)

# ---------------------------------------------------------------------------
# 步骤 5: API Key 配置
# ---------------------------------------------------------------------------
step "第 5 步: 配置 API Keys"

echo ""
echo -e "${BOLD}Codex CLI (OpenAI)${RESET}"
echo "  前往 https://platform.openai.com/api-keys 创建 API Key"
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    success "OPENAI_API_KEY 已存在于环境变量"
else
    ask "请输入 OpenAI API Key (留空跳过): "; read -rs OPENAI_KEY; echo ""
    if [[ -n "$OPENAI_KEY" ]]; then
        export OPENAI_API_KEY="$OPENAI_KEY"
        grep -q "OPENAI_API_KEY" ~/.bashrc 2>/dev/null || \
            echo "export OPENAI_API_KEY='$OPENAI_KEY'" >> ~/.bashrc
        success "OPENAI_API_KEY 已写入 ~/.bashrc"
    else
        warn "跳过 — 使用 Codex 时请确保 OPENAI_API_KEY 已设置"
    fi
fi

echo ""
echo -e "${BOLD}Claude Code CLI (Anthropic)${RESET}"
echo "  前往 https://console.anthropic.com/settings/api-keys 创建 API Key"
if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    success "ANTHROPIC_API_KEY 已存在于环境变量"
else
    ask "请输入 Anthropic API Key (留空跳过): "; read -rs ANTHROPIC_KEY; echo ""
    if [[ -n "$ANTHROPIC_KEY" ]]; then
        export ANTHROPIC_API_KEY="$ANTHROPIC_KEY"
        grep -q "ANTHROPIC_API_KEY" ~/.bashrc 2>/dev/null || \
            echo "export ANTHROPIC_API_KEY='$ANTHROPIC_KEY'" >> ~/.bashrc
        success "ANTHROPIC_API_KEY 已写入 ~/.bashrc"
    else
        warn "跳过 — 使用 Claude 时请确保 ANTHROPIC_API_KEY 已设置"
    fi
fi

# ---------------------------------------------------------------------------
# 步骤 6: QQ 机器人配置
# ---------------------------------------------------------------------------
step "第 6 步: 配置 QQ 官方机器人"

echo ""
echo -e "${BOLD}QQ 开放平台注册步骤:${RESET}"
echo "  1. 打开 https://q.qq.com  登录 QQ 开放平台"
echo "  2. 「机器人」→「创建机器人」，填写基本信息"
echo "  3. 进入机器人详情 →「开发设置」"
echo "  4. 记录以下两个值:"
echo "     - AppID     (数字，如: 102345678)"
echo "     - AppSecret (字符串，在「AppSecret」一栏查看/重置)"
echo "  5. 接入方式选择「WebSocket」长连接"
echo "  6. 开通所需「事件订阅」:"
echo "     - 群聊 @机器人消息 (GROUP_AT_MESSAGE_CREATE)"
echo "     - 单聊消息 (C2C_MESSAGE_CREATE)"
echo "     - 频道 @机器人消息 (AT_MESSAGE_CREATE，可选)"
echo ""

# 如果 config.yaml 已存在，读取现有值作为默认
EXISTING_APP_ID=""; EXISTING_SECRET=""; EXISTING_SANDBOX="false"
if [[ -f "$CONFIG_FILE" ]]; then
    EXISTING_APP_ID=$(grep 'app_id:' "$CONFIG_FILE" | head -1 | sed 's/.*app_id: *"\(.*\)"/\1/' | tr -d '"' || true)
    EXISTING_SECRET=$(grep 'app_secret:' "$CONFIG_FILE" | head -1 | sed 's/.*app_secret: *"\(.*\)"/\1/' | tr -d '"' || true)
    EXISTING_SANDBOX=$(grep 'sandbox:' "$CONFIG_FILE" | head -1 | awk '{print $2}' || echo "false")
    warn "检测到已有 config.yaml，按回车保留现有值"
fi

ask "QQ AppID${EXISTING_APP_ID:+ [当前: $EXISTING_APP_ID]}: "; read -r INPUT_APP_ID
QQ_APP_ID="${INPUT_APP_ID:-$EXISTING_APP_ID}"

ask "QQ AppSecret${EXISTING_SECRET:+ [当前: ***]}: "; read -rs INPUT_SECRET; echo ""
QQ_APP_SECRET="${INPUT_SECRET:-$EXISTING_SECRET}"

ask "是否使用沙箱环境(sandbox)? [y/N]: "; read -r INPUT_SANDBOX
QQ_SANDBOX="false"
[[ "${INPUT_SANDBOX,,}" == "y" ]] && QQ_SANDBOX="true"

if [[ -z "$QQ_APP_ID" || -z "$QQ_APP_SECRET" ]]; then
    warn "AppID 或 AppSecret 为空，跳过 QQ 连通性测试"
    QQ_CONFIGURED=false
else
    QQ_CONFIGURED=true
fi

# ---------------------------------------------------------------------------
# 步骤 7: 其他参数配置
# ---------------------------------------------------------------------------
step "第 7 步: 运行参数配置"

ask "codex exec 超时时间(秒) [默认 120]: "; read -r INPUT_TIMEOUT
EXEC_TIMEOUT="${INPUT_TIMEOUT:-120}"

ask "默认工作目录 [默认 $HOME]: "; read -r INPUT_WORKDIR
DEFAULT_WORKDIR="${INPUT_WORKDIR:-$HOME}"
DEFAULT_WORKDIR="${DEFAULT_WORKDIR/#\~/$HOME}"

ask "消息最大长度(字符,QQ群限制~2000) [默认 1800]: "; read -r INPUT_CHUNK
CHUNK_SIZE="${INPUT_CHUNK:-1800}"

# ---------------------------------------------------------------------------
# 步骤 8: 写入 config.yaml
# ---------------------------------------------------------------------------
step "第 8 步: 生成 config.yaml"

cat > "$CONFIG_FILE" << YAML
# QQ Codex Bridge — 自动生成的配置文件
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
# 如需修改，直接编辑此文件后重启服务

bot:
  app_id: "$QQ_APP_ID"
  app_secret: "$QQ_APP_SECRET"
  sandbox: $QQ_SANDBOX

gateway:
  exec_timeout: $EXEC_TIMEOUT

codex:
  binary: "$CODEX_BIN"
  default_workdir: "$DEFAULT_WORKDIR"
  reply_chunk_size: $CHUNK_SIZE
  reply_max_retries: 3
YAML

success "config.yaml 已写入: $CONFIG_FILE"

# ---------------------------------------------------------------------------
# 生成 start.sh / start_bg.sh / stop.sh (放在 config 之后，systemd 之前，确保始终生成)
# ---------------------------------------------------------------------------
PYTHON_BIN=$(command -v python3)

cat > "$SCRIPT_DIR/start.sh" << 'START'
#!/usr/bin/env bash
# 启动 QQ Codex Bridge（前台，日志直接输出）
cd "$(dirname "${BASH_SOURCE[0]}")"
exec python3 -m qq_codex_bridge.main
START

cat > "$SCRIPT_DIR/start_bg.sh" << START_BG
#!/usr/bin/env bash
# 启动 QQ Codex Bridge（后台，日志写入 bridge.log）
DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$DIR"
nohup python3 -m qq_codex_bridge.main >> "\$DIR/bridge.log" 2>&1 &
PID=\$!
echo "\$PID" > "\$DIR/bridge.pid"
echo "Started PID: \$PID"
echo "日志: tail -f \$DIR/bridge.log"
START_BG

cat > "$SCRIPT_DIR/stop.sh" << 'STOP'
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
STOP

chmod +x "$SCRIPT_DIR/start.sh" "$SCRIPT_DIR/start_bg.sh" "$SCRIPT_DIR/stop.sh"
success "便捷脚本已生成: start.sh / start_bg.sh / stop.sh"

# ---------------------------------------------------------------------------
# 步骤 9: 测试 QQ Gateway 连通性
# ---------------------------------------------------------------------------
step "第 9 步: 测试 QQ Gateway 连通性"

if [[ "$QQ_CONFIGURED" == "true" ]]; then
    BASE_URL="https://api.sgroup.qq.com"
    [[ "$QQ_SANDBOX" == "true" ]] && BASE_URL="https://sandbox.api.sgroup.qq.com"

    # Step 1: AppID + AppSecret → access_token
    info "正在换取 access_token (AppID=$QQ_APP_ID)..."
    ACCESS_TOKEN=$(python3 - <<PYEOF 2>/dev/null
import urllib.request, json, sys
data = json.dumps({"appId": "$QQ_APP_ID", "clientSecret": "$QQ_APP_SECRET"}).encode()
req  = urllib.request.Request("https://bots.qq.com/app/getAppAccessToken",
           data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print(json.loads(r.read()).get("access_token", ""))
except Exception as e:
    sys.stderr.write(str(e) + "\n")
PYEOF
    )

    if [[ -z "$ACCESS_TOKEN" ]]; then
        warn "无法获取 access_token，请检查 AppID / AppSecret 是否正确"
    else
        success "access_token 获取成功"

        # Step 2: access_token → GET /gateway/bot
        info "正在验证 Gateway 连通性..."
        HTTP_CODE=$(curl -s -o /tmp/gw_response.json -w "%{http_code}" \
            -H "Authorization: QQBot $ACCESS_TOKEN" \
            "$BASE_URL/gateway/bot" 2>/dev/null) || HTTP_CODE="ERR"

        if [[ "$HTTP_CODE" == "200" ]]; then
            WS_URL=$(python3 -c "import json; d=json.load(open('/tmp/gw_response.json')); print(d.get('url',''))" 2>/dev/null || echo "")
            success "QQ Gateway 验证通过!"
            info   "WebSocket URL: $WS_URL"
        elif [[ "$HTTP_CODE" == "ERR" ]]; then
            warn "网络连接失败（无法访问 QQ API），请检查网络或防火墙"
        else
            RESP=$(cat /tmp/gw_response.json 2>/dev/null || echo "无响应")
            warn "Gateway 返回 HTTP $HTTP_CODE: $RESP"
            warn "请检查机器人是否已在 QQ 开放平台上线"
        fi
    fi
else
    warn "跳过连通性测试（未配置凭据）"
fi

# ---------------------------------------------------------------------------
# 步骤 10: 创建 systemd 服务 (Linux)
# ---------------------------------------------------------------------------
step "第 10 步: 配置后台服务 (systemd)"

HAS_SYSTEMD=false
command -v systemctl &>/dev/null && [[ -d /etc/systemd/system ]] && HAS_SYSTEMD=true

if [[ "$HAS_SYSTEMD" == "true" ]]; then
    ask "是否创建 systemd 服务 (开机自启)? [Y/n]: "; read -r CREATE_SERVICE
    if [[ "${CREATE_SERVICE,,}" != "n" ]]; then
        RUN_USER=$(whoami)
        cat > /tmp/qq-codex-bridge.service << SERVICE
[Unit]
Description=QQ Codex Bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PYTHON_BIN -m qq_codex_bridge.main
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONPATH=$SCRIPT_DIR
EnvironmentFile=-$SCRIPT_DIR/.env

[Install]
WantedBy=multi-user.target
SERVICE

        if [[ "$(id -u)" -eq 0 ]]; then
            cp /tmp/qq-codex-bridge.service "$SERVICE_FILE"
            if systemctl daemon-reload 2>/dev/null && systemctl enable qq-codex-bridge 2>/dev/null; then
                success "systemd 服务已创建并设为开机自启"
            else
                warn "systemd 服务文件已写入 $SERVICE_FILE，但 daemon-reload 失败"
                warn "请手动执行: systemctl daemon-reload && systemctl enable qq-codex-bridge"
            fi
        else
            warn "需要 root 权限安装 systemd 服务，请运行:"
            echo "  sudo cp /tmp/qq-codex-bridge.service $SERVICE_FILE"
            echo "  sudo systemctl daemon-reload"
            echo "  sudo systemctl enable --now qq-codex-bridge"
        fi
    fi
else
    info "非 systemd 系统，跳过服务注册"
fi


# ---------------------------------------------------------------------------
# 完成 — 使用说明
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}${GREEN}  安装完成!${RESET}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "${BOLD}启动方式:${RESET}"
echo ""
echo -e "  ${CYAN}前台运行（看实时日志）:${RESET}"
echo "    cd $SCRIPT_DIR && ./start.sh"
echo ""
echo -e "  ${CYAN}后台运行（nohup）:${RESET}"
echo "    cd $SCRIPT_DIR && ./start_bg.sh"
echo "    查看日志: tail -f $SCRIPT_DIR/bridge.log"
echo "    停止服务: ./stop.sh"
echo ""
if [[ "$HAS_SYSTEMD" == "true" && "${CREATE_SERVICE,,}" != "n" ]]; then
echo -e "  ${CYAN}systemd 服务管理:${RESET}"
echo "    启动: sudo systemctl start qq-codex-bridge"
echo "    停止: sudo systemctl stop qq-codex-bridge"
echo "    状态: sudo systemctl status qq-codex-bridge"
echo "    日志: sudo journalctl -u qq-codex-bridge -f"
echo ""
fi
echo -e "${BOLD}在 QQ 群里 @机器人 发送:${RESET}"
echo "    /help           — 查看所有命令"
echo "    /model claude   — 切换到 Claude CLI"
echo "    /model codex    — 切换到 Codex CLI"
echo "    /pwd            — 查看当前工作目录"
echo "    /cd /your/path  — 切换工作目录"
echo "    其他任意文字    — 转发给当前激活的 CLI"
echo ""
echo -e "${BOLD}配置文件:${RESET} $CONFIG_FILE"
echo -e "${BOLD}修改配置后重启服务生效${RESET}"
echo ""
