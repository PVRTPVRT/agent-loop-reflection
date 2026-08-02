"""Provider-neutral LLM interface and OpenAI Responses API implementation."""

from __future__ import annotations

import os
from collections import deque
from collections.abc import Iterable, Mapping
from typing import Literal, Protocol

from openai import OpenAI

from agentloop.models import LLMRequest, LLMResponse, TokenUsage


class LLMProvider(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate one model response."""


class OpenAIResponsesProvider:
    """OpenAI provider using the Responses API.

    The model remains configurable so benchmarks can compare quality, latency,
    and cost without changing application code.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        default_model: str | None = None,
        reasoning_effort: Literal["low", "medium", "high"] | None = None,
        text_format: Mapping[str, object] | None = None,
        client: OpenAI | None = None,
    ) -> None:
        self.default_model = default_model or os.environ.get("OPENAI_MODEL") or "gpt-5.4-nano"
        self.reasoning_effort = reasoning_effort
        self.text_format = text_format
        self._client = client or OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def generate(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        kwargs = {
            "model": model,
            "instructions": request.system_prompt or None,
            "input": request.user_prompt,
            "max_output_tokens": request.max_output_tokens,
            "metadata": request.metadata or None,
            "store": False,
        }
        if self.reasoning_effort is not None:
            kwargs["reasoning"] = {"effort": self.reasoning_effort}
        if self.text_format is not None:
            kwargs["text"] = {"format": dict(self.text_format)}
        response = self._client.responses.create(**kwargs)
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


class FakeLLMProvider:
    """Deterministic provider for tests and offline workflow development."""

    def __init__(self, responses: Iterable[str | LLMResponse]) -> None:
        self._responses = deque(responses)
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if not self._responses:
            raise RuntimeError("FakeLLMProvider has no responses remaining")
        response = self._responses.popleft()
        if isinstance(response, LLMResponse):
            return response
        return LLMResponse(text=response, model=request.model or "fake-model")
