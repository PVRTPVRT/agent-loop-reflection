"""Typed evidence passed from a failed Direct route into repair mode."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentloop.evaluation_v2_models import EvaluationSuite


class RepairAttempt(BaseModel):
    """One failed repair observation retained to prevent hypothesis cycles."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    round_number: int = Field(ge=0)
    diagnosis: str = Field(min_length=1)
    verification_message: str = Field(min_length=1)


class RepairContext(BaseModel):
    """Immutable evidence for repairing one failed Direct candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str = Field(min_length=1)
    failed_code: str = Field(min_length=1)
    routing_suite: EvaluationSuite
    verification_message: str = Field(min_length=1)
    attempts: tuple[RepairAttempt, ...] = ()

    @model_validator(mode="after")
    def require_failed_evidence(self) -> RepairContext:
        if not self.failed_code.strip():
            raise ValueError("failed_code must contain executable candidate code")
        if not self.verification_message.strip():
            raise ValueError("verification_message must describe the route failure")
        round_numbers = [attempt.round_number for attempt in self.attempts]
        if round_numbers != sorted(set(round_numbers)):
            raise ValueError("repair attempt rounds must be unique and increasing")
        return self
