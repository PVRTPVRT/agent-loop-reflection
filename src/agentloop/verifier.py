"""Code verification result and protocol."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from agentloop.models import TestSuite


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    success: bool
    message: str


class CodeVerifier(Protocol):
    def verify(self, code: str, suite: TestSuite) -> VerificationResult:
        """Verify code against the supplied test suite."""
