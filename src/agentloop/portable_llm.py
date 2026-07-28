"""OpenAI provider variant with explicit reasoning controls for portability."""

from __future__ import annotations

from typing import Literal

from openai import OpenAI

from agentloop.models import LLMRequest, LLMResponse, TokenUsage

ReasoningEffort = Literal["none", "low", "medium", "high"]


class PortableOpenAIProvider:
    """Responses API provider with explicit reasoning and output budgets.

    Small reasoning models can consume their output budget before producing
    visible text. Setting effort and a minimum output budget makes that
    behavior explicit and benchmarkable.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: ReasoningEffort = "low",
        minimum_output_tokens: int = 4_000,
        client: OpenAI | None = None,
    ) -> None:
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.minimum_output_tokens = minimum_output_tokens
        self._client = client or OpenAI(api_key=api_key)

    def generate(self, request: LLMRequest) -> LLMResponse:
        response = self._client.responses.create(
            model=request.model or self.model,
            instructions=request.system_prompt or None,
            input=request.user_prompt,
            max_output_tokens=max(
                request.max_output_tokens,
                self.minimum_output_tokens,
            ),
            metadata=request.metadata or None,
            reasoning={"effort": self.reasoning_effort},
            store=False,
        )
        usage = response.usage
        input_details = getattr(usage, "input_tokens_details", None)
        return LLMResponse(
            text=response.output_text,
            model=response.model,
            response_id=response.id,
            usage=TokenUsage(
                input_tokens=getattr(usage, "input_tokens", 0),
                output_tokens=getattr(usage, "output_tokens", 0),
                total_tokens=getattr(usage, "total_tokens", 0),
                cached_input_tokens=getattr(input_details, "cached_tokens", 0),
            ),
        )
