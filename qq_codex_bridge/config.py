"""
Configuration loader for QQ Codex Bridge.
Reads from environment variables with fallback to config.yaml.
"""
from __future__ import annotations

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class BotConfig:
    app_id: str
    app_secret: str
    sandbox: bool = False


@dataclass
class GatewayConfig:
    # Seconds of CLI output silence before treating response as complete
    idle_timeout: float = 3.0


@dataclass
class CodexConfig:
    # Path to codex binary; defaults to $PATH lookup
    binary: str = "codex"
    # Default working directory for new sessions
    default_workdir: str = str(Path.home())
    # Max length of a single reply chunk (QQ message limit ~2000 chars)
    reply_chunk_size: int = 1800
    # Max retries for reply delivery
    reply_max_retries: int = 3


@dataclass
class AppConfig:
    bot: BotConfig
    gateway: GatewayConfig = field(default_factory=GatewayConfig)
    codex: CodexConfig = field(default_factory=CodexConfig)


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Load config from YAML file, then override with environment variables.

    Environment variables (all optional if YAML is present):
      QQ_APP_ID, QQ_APP_SECRET, QQ_SANDBOX
      EXEC_TIMEOUT
      CODEX_BINARY, CODEX_DEFAULT_WORKDIR, REPLY_CHUNK_SIZE, REPLY_MAX_RETRIES
    """
    raw: dict = {}

    # 1. Load YAML if provided or auto-detect
    search_paths = [config_path] if config_path else [
        "config.yaml",
        "config.yml",
        str(Path(__file__).parent / "config.yaml"),
    ]
    for p in search_paths:
        if p and Path(p).exists():
            with open(p) as f:
                raw = yaml.safe_load(f) or {}
            break

    bot_raw = raw.get("bot", {})
    gw_raw = raw.get("gateway", {})
    cx_raw = raw.get("codex", {})

    # 2. Environment variables override YAML
    bot = BotConfig(
        app_id=os.environ.get("QQ_APP_ID", bot_raw.get("app_id", "")),
        app_secret=os.environ.get("QQ_APP_SECRET", bot_raw.get("app_secret", "")),
        sandbox=os.environ.get("QQ_SANDBOX", str(bot_raw.get("sandbox", False))).lower()
        in ("1", "true", "yes"),
    )

    gateway = GatewayConfig(
        idle_timeout=float(os.environ.get("IDLE_TIMEOUT", gw_raw.get("idle_timeout", 3.0))),
    )

    codex = CodexConfig(
        binary=os.environ.get("CODEX_BINARY", cx_raw.get("binary", "codex")),
        default_workdir=os.environ.get(
            "CODEX_DEFAULT_WORKDIR",
            cx_raw.get("default_workdir", str(Path.home())),
        ),
        reply_chunk_size=int(
            os.environ.get("REPLY_CHUNK_SIZE", cx_raw.get("reply_chunk_size", 1800))
        ),
        reply_max_retries=int(
            os.environ.get("REPLY_MAX_RETRIES", cx_raw.get("reply_max_retries", 3))
        ),
    )

    return AppConfig(bot=bot, gateway=gateway, codex=codex)
