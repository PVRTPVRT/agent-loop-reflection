"""OpenAI Responses provider with schema-constrained Tester output."""

from __future__ import annotations

from typing import Literal

from openai import OpenAI

from agentloop.models import LLMRequest, LLMResponse, TokenUsage

ReasoningEffort = Literal["none", "low", "medium", "high"]

TEST_SUITE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "function_name": {"type": "string", "minLength": 1},
        "test_cases": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "args": {"type": "array", "items": {}},
                    "expected": {},
                    "description": {"type": "string"},
                },
                "required": ["args", "expected", "description"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["function_name", "test_cases"],
    "additionalProperties": False,
}


class StructuredOutputError(RuntimeError):
    """Raised when the API finishes without returning visible output."""


class StructuredOpenAIProvider:
    """Use JSON Schema for Tester calls and ordinary text for other agents."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: ReasoningEffort = "none",
        minimum_output_tokens: int = 4_000,
        client: OpenAI | None = None,
    ) -> None:
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.minimum_output_tokens = minimum_output_tokens
        self._client = client or OpenAI(api_key=api_key)

    def generate(self, request: LLMRequest) -> LLMResponse:
        kwargs = {
            "model": request.model or self.model,
            "instructions": request.system_prompt or None,
            "input": request.user_prompt,
            "max_output_tokens": max(
                request.max_output_tokens,
                self.minimum_output_tokens,
            ),
            "metadata": request.metadata or None,
            "reasoning": {"effort": self.reasoning_effort},
            "store": False,
        }
        if request.metadata.get("agent") == "tester":
            kwargs["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "test_suite",
                    "description": "A deterministic executable test suite for one function.",
                    "schema": TEST_SUITE_JSON_SCHEMA,
                    "strict": True,
                }
            }

        response = self._client.responses.create(**kwargs)
        output_text = response.output_text
        if not output_text:
            status = getattr(response, "status", "unknown")
            details = getattr(response, "incomplete_details", None)
            raise StructuredOutputError(
                f"OpenAI response contained no visible output "
                f"(status={status}, incomplete_details={details})"
            )

        usage = response.usage
        input_details = getattr(usage, "input_tokens_details", None)
        return LLMResponse(
            text=output_text,
            model=response.model,
            response_id=response.id,
            usage=TokenUsage(
                input_tokens=getattr(usage, "input_tokens", 0),
                output_tokens=getattr(usage, "output_tokens", 0),
                total_tokens=getattr(usage, "total_tokens", 0),
                cached_input_tokens=getattr(input_details, "cached_tokens", 0),
            ),
        )
