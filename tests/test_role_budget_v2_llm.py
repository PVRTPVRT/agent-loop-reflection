from types import SimpleNamespace

from agentloop.models import LLMRequest
from agentloop.role_budget_v2_llm import RoleBudgetV2Provider


class StubResponses:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            id="role-budget",
            model="gpt-test",
            output_text="[APPROVED]",
            status="completed",
            incomplete_details=None,
            usage=SimpleNamespace(
                input_tokens=1,
                output_tokens=1,
                total_tokens=2,
                input_tokens_details=None,
            ),
        )


def test_critic_output_is_capped_at_500_tokens() -> None:
    responses = StubResponses()
    provider = RoleBudgetV2Provider.__new__(RoleBudgetV2Provider)
    provider.model = "gpt-test"
    provider.reasoning_effort = "none"
    provider.minimum_output_tokens = 4_000
    provider._client = SimpleNamespace(responses=responses)

    provider.generate(
        LLMRequest(
            user_prompt="review",
            metadata={"agent": "critic"},
        )
    )

    assert responses.calls[0]["max_output_tokens"] == 500
    assert provider.minimum_output_tokens == 4_000
