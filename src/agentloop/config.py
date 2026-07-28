"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace


class ConfigurationError(ValueError):
    """Raised when application configuration is invalid."""


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} 必须是整数") from exc
    if value < 1:
        raise ConfigurationError(f"{name} 必须大于 0")
    return value


@dataclass(frozen=True, slots=True)
class AppSettings:
    openai_api_key: str | None
    model: str = "gpt-5.6-luna"
    max_debate_rounds: int = 2
    max_coding_rounds: int = 3

    @classmethod
    def from_env(cls) -> AppSettings:
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            model=os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"),
            max_debate_rounds=_positive_int("MAX_DEBATE_ROUNDS", 2),
            max_coding_rounds=_positive_int("MAX_CODING_ROUNDS", 3),
        )

    def with_model(self, model: str | None) -> AppSettings:
        if model is None:
            return self
        cleaned = model.strip()
        if not cleaned:
            raise ConfigurationError("模型名称不能为空")
        return replace(self, model=cleaned)

    def require_api_key(self) -> str:
        if not self.openai_api_key:
            raise ConfigurationError(
                "缺少 OPENAI_API_KEY。请复制 .env.example 的配置方式，并在当前终端设置环境变量。"
            )
        return self.openai_api_key
