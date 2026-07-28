"""Typed evidence passed from a failed Direct route into repair mode."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentloop.evaluation_v2_models import EvaluationSuite


class RepairContext(BaseModel):
    """Immutable evidence for repairing one failed Direct candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str = Field(min_length=1)
    failed_code: str = Field(min_length=1)
    routing_suite: EvaluationSuite
    verification_message: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_failed_evidence(self) -> RepairContext:
        if not self.failed_code.strip():
            raise ValueError("failed_code must contain executable candidate code")
        if not self.verification_message.strip():
            raise ValueError("verification_message must describe the route failure")
        return self
