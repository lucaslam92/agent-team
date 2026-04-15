# QQ Codex Bridge

QQ 官方机器人 × Codex / Claude Code CLI 转接服务。

在 QQ 群 / 频道 / 私聊中 @机器人，消息通过 WebSocket 长连接转发给本地 CLI（Codex 或 Claude Code），执行结果自动回复。

---

## 架构

```
QQ 用户 @机器人
      │
      ▼
QQ 官方平台（WebSocket 推送）
      │
      ▼
BotGatewayClient          ← gateway/ws_client.py
  · Hello / Identify / Resume
  · 心跳保活
  · 断线自动重连（指数退避）
      │
      ▼
Message Router            ← router/message.py
  · 剥离 @mention 标记
  · 解析附件（图片 / 视频）
  · 统一为 IncomingMessage
      │
      ▼
Command Layer             ← router/command.py
  · /help /status /pwd /cd /clear /model
  · 本地处理，不进入 CLI
      │
      ▼（非命令消息）
Executor                  ← bridge/executor.py
  · 下载图片附件到本地临时目录
  · 按 session.model 选择后端：
      codex → `codex exec --cwd <dir> [--image ...] -- <prompt>`
      claude → `claude -p <prompt> [--image ...]`
  · 超时强制 kill，捕获 stdout / stderr
  · 剥离 ANSI 转义码
      │
      ▼
Reply Sender              ← reply/sender.py
  · 超长输出自动分块（默认 1800 字符/条）
  · 指数退避重试（最多 3 次）
  · 支持 group / channel / C2C 三种 QQ API 路径
      │
      ▼
QQ 用户收到回复
```

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/lucaslam92/agent-team.git
cd agent-team
git checkout feat/qq-codex-bridge
```

### 2. 一键安装 & 配置

```bash
bash setup.sh
```

向导步骤：

| 步骤 | 内容 |
|------|------|
| 1 | 检查 Python 3.10+ / Node.js / npm |
| 2 | 安装 Python 依赖（`pip install -r requirements.txt`）|
| 3 | 安装 / 升级 Codex CLI（`@openai/codex`）|
| 4 | 安装 / 升级 Claude Code CLI（`@anthropic-ai/claude-code`）|
| 5 | 配置 OpenAI + Anthropic API Key |
| 6 | 填入 QQ App ID + Token |
| 7 | 设置运行参数（超时 / 工作目录 / 消息长度）|
| 8 | 生成 `config.yaml` 及启停脚本 |
| 9 | 在线测试 QQ Gateway 连通性 |
| 10 | 可选：注册 systemd 服务（开机自启）|

### 3. 获取 QQ 机器人凭据

1. 打开 [q.qq.com](https://q.qq.com) 登录 QQ 开放平台
2. **机器人** → **创建机器人**，填写基本信息
3. 进入机器人详情 → **开发设置**，记录：
   - **AppID**（数字，如 `102345678`）
   - **Token**（长字符串）
4. 接入方式选择 **WebSocket 长连接**
5. 开通事件订阅：
   - `GROUP_AT_MESSAGE_CREATE`（群聊 @机器人）
   - `C2C_MESSAGE_CREATE`（私聊）
   - `AT_MESSAGE_CREATE`（频道 @机器人，可选）

---

## 启动 / 停止

| 方式 | 命令 |
|------|------|
| 前台运行（实时日志）| `./start.sh` |
| 后台运行（nohup）| `./start_bg.sh` |
| 停止后台服务 | `./stop.sh` |
| 查看后台日志 | `tail -f bridge.log` |
| systemd 启动 | `sudo systemctl start qq-codex-bridge` |
| systemd 停止 | `sudo systemctl stop qq-codex-bridge` |
| systemd 日志 | `sudo journalctl -u qq-codex-bridge -f` |

---

## 配置文件

`config.yaml`（由 `setup.sh` 自动生成，可手动修改）：

```yaml
bot:
  app_id: "YOUR_QQ_APP_ID"
  token:  "YOUR_QQ_BOT_TOKEN"
  sandbox: false          # true = 使用沙箱 API 端点

gateway:
  exec_timeout: 120       # CLI 执行超时（秒）

codex:
  binary: "codex"         # codex 可执行文件路径
  default_workdir: "~"    # 新会话的默认工作目录
  reply_chunk_size: 1800  # 单条 QQ 消息最大字符数
  reply_max_retries: 3    # 回复失败最大重试次数
```

**修改配置后重启服务生效。**

环境变量优先级高于 YAML，可用于 CI / Docker 部署：

```bash
export QQ_APP_ID=102345678
export QQ_TOKEN=your_token
export EXEC_TIMEOUT=120
```

---

## QQ 群内命令

在群里 @机器人 后发送：

| 命令 | 说明 |
|------|------|
| `/help` | 查看所有命令 |
| `/status` | 查看服务状态、当前 model、CLI 版本 |
| `/model codex` | 切换到 Codex CLI |
| `/model claude` | 切换到 Claude Code CLI |
| `/pwd` | 查看当前会话工作目录 |
| `/cd <路径>` | 切换工作目录 |
| `/clear` | 重置工作目录为默认值 |
| 其他任意文字 | 转发给当前激活的 CLI 执行 |

> 附带图片时，图片会被下载到本地临时目录，以 `--image <path>` 参数传给 CLI。

### 会话隔离

- **群聊**：同一个群共享一个工作目录和 model 状态
- **私聊 / 频道**：每个用户独立的工作目录和 model 状态
- 重启服务后会话状态重置（内存存储）

---

## 依赖

| 包 | 用途 |
|----|------|
| `websockets` | QQ Gateway WebSocket 客户端 |
| `aiohttp` | QQ REST API 回复 + 附件下载 |
| `pyyaml` | 配置文件解析 |

CLI 工具：

| 工具 | 安装 |
|------|------|
| Codex CLI | `npm install -g @openai/codex` |
| Claude Code CLI | `npm install -g @anthropic-ai/claude-code` |

---

## 项目结构

```
agent-team/
├── setup.sh                      # 一键安装 & 配置引导
├── start.sh                      # 前台启动
├── start_bg.sh                   # 后台启动（nohup）
├── stop.sh                       # 停止服务
├── config.yaml.example           # 配置示例
├── requirements.txt              # Python 依赖
└── qq_codex_bridge/
    ├── main.py                   # 入口 & 消息分发
    ├── config.py                 # 配置加载（YAML + 环境变量）
    ├── gateway/
    │   ├── ws_client.py          # QQ WebSocket 网关客户端
    │   └── models.py             # 数据类（IncomingMessage 等）
    ├── router/
    │   ├── message.py            # 消息规范化
    │   └── command.py            # 内置命令处理
    ├── bridge/
    │   ├── executor.py           # 统一 CLI 执行器（codex / claude）
    │   ├── codex.py              # ExecResult 数据类 + ANSI 剥离
    │   └── context.py            # 会话状态管理
    └── reply/
        └── sender.py             # QQ API 回复发送（分块 + 重试）
```
