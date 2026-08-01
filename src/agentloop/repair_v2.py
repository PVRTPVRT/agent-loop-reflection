"""Typed evidence passed from a failed Direct route into repair mode."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentloop.evaluation_boundary import (
    CandidateArtifact,
    EvaluationSpec,
    function_case_spec,
    require_function_suite,
    require_source_code,
    source_code_artifact,
)
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
    candidate_artifact: CandidateArtifact
    evaluation_spec: EvaluationSpec
    verification_message: str = Field(min_length=1)
    attempts: tuple[RepairAttempt, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_function_fields(cls, value: Any) -> Any:
        """Translate the v0.3 constructor without preserving duplicate state."""
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "failed_code" in data:
            if "candidate_artifact" in data:
                raise ValueError("provide candidate_artifact or failed_code, not both")
            data["candidate_artifact"] = source_code_artifact(data.pop("failed_code"))
        if "routing_suite" in data:
            if "evaluation_spec" in data:
                raise ValueError("provide evaluation_spec or routing_suite, not both")
            data["evaluation_spec"] = function_case_spec(data.pop("routing_suite"))
        return data

    @model_validator(mode="after")
    def require_failed_evidence(self) -> RepairContext:
        if not self.verification_message.strip():
            raise ValueError("verification_message must describe the route failure")
        round_numbers = [attempt.round_number for attempt in self.attempts]
        if round_numbers != sorted(set(round_numbers)):
            raise ValueError("repair attempt rounds must be unique and increasing")
        return self

    @property
    def failed_code(self) -> str:
        """Compatibility view for the current source-code repair agents."""
        return require_source_code(self.candidate_artifact)

    @property
    def routing_suite(self) -> EvaluationSuite:
        """Compatibility view for the current function-case repair workflow."""
        return require_function_suite(self.evaluation_spec)
