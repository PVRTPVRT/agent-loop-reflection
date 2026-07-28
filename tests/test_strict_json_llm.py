from types import SimpleNamespace

from agentloop.models import LLMRequest
from agentloop.strict_json_llm import StrictJSONOpenAIProvider


class StubResponses:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="strict-response",
            model="gpt-test",
            output_text=(
                '{"function_name":"add","test_cases":'
                '[{"args":[1,2],"expected":3,"description":"basic"}]}'
            ),
            status="completed",
            incomplete_details=None,
            usage=SimpleNamespace(
                input_tokens=1,
                output_tokens=1,
                total_tokens=2,
                input_tokens_details=None,
            ),
        )


def test_strict_schema_types_every_dynamic_value() -> None:
    responses = StubResponses()
    provider = StrictJSONOpenAIProvider(
        api_key="test",
        model="gpt-test",
        client=SimpleNamespace(responses=responses),
    )

    provider.generate(LLMRequest(user_prompt="tests", metadata={"agent": "tester"}))

    schema = responses.kwargs["text"]["format"]["schema"]
    case_properties = schema["properties"]["test_cases"]["items"]["properties"]
    assert "anyOf" in case_properties["args"]["items"]
    assert "anyOf" in case_properties["expected"]
