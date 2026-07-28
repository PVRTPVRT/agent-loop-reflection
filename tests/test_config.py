import pytest

from agentloop.config import AppSettings, ConfigurationError


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("MAX_DEBATE_ROUNDS", "4")
    monkeypatch.setenv("MAX_CODING_ROUNDS", "5")

    settings = AppSettings.from_env()

    assert settings.openai_api_key == "test-key"
    assert settings.model == "test-model"
    assert settings.max_debate_rounds == 4
    assert settings.max_coding_rounds == 5


def test_settings_reject_invalid_round_limit(monkeypatch) -> None:
    monkeypatch.setenv("MAX_DEBATE_ROUNDS", "0")
    with pytest.raises(ConfigurationError, match="大于 0"):
        AppSettings.from_env()


def test_settings_require_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        AppSettings.from_env().require_api_key()
