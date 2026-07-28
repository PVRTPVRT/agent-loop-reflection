from types import SimpleNamespace

import pytest

from agentloop.models import LLMRequest
from agentloop.structured_llm import (
    StructuredOpenAIProvider,
    StructuredOutputError,
)


class StubResponses:
    def __init__(self, output_text: str = '{"function_name":"f","test_cases":[]}') -> None:
        self.output_text = output_text
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="structured-response",
            model="gpt-test",
            output_text=self.output_text,
            status="completed",
            incomplete_details=None,
            usage=SimpleNamespace(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                input_tokens_details=SimpleNamespace(cached_tokens=0),
            ),
        )


def make_provider(responses: StubResponses) -> StructuredOpenAIProvider:
    return StructuredOpenAIProvider(
        api_key="test-key",
        model="gpt-test",
        client=SimpleNamespace(responses=responses),
    )


def test_tester_request_uses_strict_json_schema() -> None:
    responses = StubResponses()
    provider = make_provider(responses)

    provider.generate(
        LLMRequest(
            user_prompt="build tests",
            metadata={"agent": "tester", "task_id": "task-1"},
        )
    )

    output_format = responses.kwargs["text"]["format"]
    assert output_format["type"] == "json_schema"
    assert output_format["strict"] is True
    assert output_format["schema"]["required"] == ["function_name", "test_cases"]
    assert responses.kwargs["reasoning"] == {"effort": "none"}


def test_non_tester_request_does_not_force_json_schema() -> None:
    responses = StubResponses("def f(): pass")
    provider = make_provider(responses)

    provider.generate(LLMRequest(user_prompt="write code", metadata={"agent": "coder"}))

    assert "text" not in responses.kwargs


def test_empty_output_reports_response_status() -> None:
    provider = make_provider(StubResponses(""))

    with pytest.raises(StructuredOutputError, match="status=completed"):
        provider.generate(LLMRequest(user_prompt="build tests", metadata={"agent": "tester"}))
