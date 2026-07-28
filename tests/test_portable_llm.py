from types import SimpleNamespace

from agentloop.models import LLMRequest
from agentloop.portable_llm import PortableOpenAIProvider


class StubResponses:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="portable-response",
            model="gpt-test",
            output_text='{"ok": true}',
            usage=SimpleNamespace(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                input_tokens_details=SimpleNamespace(cached_tokens=0),
            ),
        )


def test_portable_provider_sets_reasoning_and_minimum_budget() -> None:
    responses = StubResponses()
    client = SimpleNamespace(responses=responses)
    provider = PortableOpenAIProvider(
        api_key="test-key",
        model="gpt-test",
        reasoning_effort="low",
        minimum_output_tokens=4_000,
        client=client,
    )

    result = provider.generate(LLMRequest(user_prompt="return json"))

    assert responses.kwargs["reasoning"] == {"effort": "low"}
    assert responses.kwargs["max_output_tokens"] == 4_000
    assert responses.kwargs["store"] is False
    assert result.text == '{"ok": true}'
    assert result.usage.total_tokens == 30
