from types import SimpleNamespace

import pytest

from agentloop.llm import FakeLLMProvider, OpenAIResponsesProvider
from agentloop.models import LLMRequest


class StubResponses:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp_test",
            model="gpt-test",
            output_text="generated text",
            usage=SimpleNamespace(
                input_tokens=12,
                output_tokens=5,
                total_tokens=17,
                input_tokens_details=SimpleNamespace(cached_tokens=4),
            ),
        )


def test_openai_provider_uses_responses_api_and_maps_usage() -> None:
    responses = StubResponses()
    client = SimpleNamespace(responses=responses)
    provider = OpenAIResponsesProvider(
        default_model="gpt-test",
        client=client,
    )

    result = provider.generate(
        LLMRequest(
            system_prompt="Be precise.",
            user_prompt="Write a function.",
            metadata={"agent": "coder"},
        )
    )

    assert responses.kwargs == {
        "model": "gpt-test",
        "instructions": "Be precise.",
        "input": "Write a function.",
        "max_output_tokens": 2_000,
        "metadata": {"agent": "coder"},
        "store": False,
    }
    assert result.text == "generated text"
    assert result.usage.total_tokens == 17
    assert result.usage.cached_input_tokens == 4


def test_openai_provider_defaults_to_validated_low_cost_model(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    provider = OpenAIResponsesProvider(client=SimpleNamespace(responses=StubResponses()))

    assert provider.default_model == "gpt-5.4-nano"


def test_openai_provider_can_set_reasoning_and_structured_text_format() -> None:
    responses = StubResponses()
    text_format = {"type": "json_schema", "name": "result", "schema": {"type": "object"}}
    provider = OpenAIResponsesProvider(
        default_model="gpt-test",
        reasoning_effort="low",
        text_format=text_format,
        client=SimpleNamespace(responses=responses),
    )

    provider.generate(LLMRequest(user_prompt="repair it"))

    assert responses.kwargs["reasoning"] == {"effort": "low"}
    assert responses.kwargs["text"] == {"format": text_format}


def test_fake_provider_is_deterministic_and_records_requests() -> None:
    provider = FakeLLMProvider(["first", "second"])
    request = LLMRequest(user_prompt="hello")

    assert provider.generate(request).text == "first"
    assert provider.generate(request).text == "second"
    assert provider.requests == [request, request]


def test_fake_provider_fails_when_queue_is_empty() -> None:
    provider = FakeLLMProvider([])
    with pytest.raises(RuntimeError, match="no responses remaining"):
        provider.generate(LLMRequest(user_prompt="hello"))
