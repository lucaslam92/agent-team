"""
Multi-model LLM client abstraction.

Supports:
  - Anthropic (claude-opus-4-6, claude-sonnet-4-6, ...)
  - OpenAI-compatible APIs (GPT-4o, local Ollama, any openai-sdk-compatible endpoint)

Each agent picks its own model via settings.yaml.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMConfig:
    provider: str       # "anthropic" | "openai"
    model: str
    api_key: str
    base_url: str | None = None   # For OpenAI-compatible endpoints
    max_tokens: int = 4096
    thinking: bool = True         # Adaptive thinking (Anthropic only)


class LLMClient:
    """Unified chat interface over multiple providers."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        if self.config.provider == "anthropic":
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.config.api_key)
        elif self.config.provider == "openai":
            import openai
            kwargs: dict = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = openai.OpenAI(**kwargs)
        else:
            raise ValueError(f"Unknown provider: {self.config.provider!r}")

    def chat(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
    ) -> str:
        """
        Send a single user turn and return the assistant text.
        Uses streaming internally to avoid timeouts on long generations.
        """
        tokens = max_tokens or self.config.max_tokens

        if self.config.provider == "anthropic":
            return self._anthropic_chat(system, user, tokens)
        else:
            return self._openai_chat(system, user, tokens)

    # ── Anthropic ────────────────────────────────────────────────────────────

    def _anthropic_chat(self, system: str, user: str, max_tokens: int) -> str:
        kwargs: dict = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if self.config.thinking:
            kwargs["thinking"] = {"type": "adaptive"}

        with self._client.messages.stream(**kwargs) as stream:
            response = stream.get_final_message()

        return next(b.text for b in response.content if b.type == "text")

    # ── OpenAI-compatible ─────────────────────────────────────────────────────

    def _openai_chat(self, system: str, user: str, max_tokens: int) -> str:
        response = self._client.chat.completions.create(
            model=self.config.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return response.choices[0].message.content or ""


def client_from_settings(agent_cfg: dict, global_cfg: dict) -> LLMClient:
    """
    Build an LLMClient from settings.yaml structure:

    llm:
      default:
        provider: anthropic
        model: claude-opus-4-6
        api_key_env: ANTHROPIC_API_KEY
        thinking: true
      planner:
        model: claude-opus-4-6       # override model only
      coder:
        model: claude-opus-4-6
        max_tokens: 8192
      evaluator:
        model: claude-sonnet-4-6     # cheaper for eval

    agent_cfg is the per-agent dict; global_cfg is llm.default.
    """
    import os

    def resolve(key: str, fallback: Any = None) -> Any:
        return agent_cfg.get(key, global_cfg.get(key, fallback))

    provider = resolve("provider", "anthropic")
    model    = resolve("model", "claude-opus-4-6")

    api_key_env = resolve("api_key_env", "ANTHROPIC_API_KEY")
    api_key     = resolve("api_key") or os.environ.get(api_key_env, "")
    if not api_key:
        raise RuntimeError(
            f"API key not found. Set env var {api_key_env!r} or provide api_key in settings.yaml"
        )

    return LLMClient(LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=resolve("base_url"),
        max_tokens=int(resolve("max_tokens", 4096)),
        thinking=bool(resolve("thinking", True)),
    ))
