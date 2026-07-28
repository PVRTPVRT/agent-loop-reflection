"""Typed domain models shared across agents, providers, and evaluations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CodingTask(StrictModel):
    task_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    category: str = "general"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TestCase(StrictModel):
    args: list[Any]
    expected: Any
    description: str = ""


class TestSuite(StrictModel):
    function_name: str = Field(min_length=1)
    test_cases: list[TestCase] = Field(min_length=1)

    @model_validator(mode="after")
    def ensure_unique_cases(self) -> TestSuite:
        serialized = [case.model_dump_json(exclude={"description"}) for case in self.test_cases]
        if len(serialized) != len(set(serialized)):
            raise ValueError("test_cases must not contain duplicates")
        return self


class LLMRequest(StrictModel):
    system_prompt: str = ""
    user_prompt: str = Field(min_length=1)
    model: str | None = None
    max_output_tokens: int = Field(default=2_000, ge=1, le=100_000)
    metadata: dict[str, str] = Field(default_factory=dict)


class TokenUsage(StrictModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)


class LLMResponse(StrictModel):
    text: str
    model: str
    response_id: str | None = None
    usage: TokenUsage = Field(default_factory=TokenUsage)


class AgentEvent(StrictModel):
    agent: Literal["tester", "critic", "coder", "verifier", "workflow"]
    event_type: str = Field(min_length=1)
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
