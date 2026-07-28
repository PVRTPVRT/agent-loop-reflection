"""V2 provider with explicit network timeout and retry budgets."""

from __future__ import annotations

from openai import OpenAI

from agentloop.strict_v2_llm import StrictV2OpenAIProvider


class BoundedStrictV2Provider(StrictV2OpenAIProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort="none",
        request_timeout_seconds: float = 30.0,
        max_retries: int = 1,
    ) -> None:
        client = OpenAI(
            api_key=api_key,
            timeout=request_timeout_seconds,
            max_retries=max_retries,
        )
        super().__init__(
            api_key=api_key,
            model=model,
            reasoning_effort=reasoning_effort,
            client=client,
        )
        self.request_timeout_seconds = request_timeout_seconds
        self.max_retries = max_retries
