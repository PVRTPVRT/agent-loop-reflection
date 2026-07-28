"""Code verification boundary."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from agentloop.models import TestSuite
from agentloop.sandbox import DockerSandbox, SandboxUnavailableError


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    success: bool
    message: str


class CodeVerifier(Protocol):
    def verify(self, code: str, suite: TestSuite) -> VerificationResult:
        """Verify code against the supplied test suite."""


class SandboxCodeVerifier:
    def __init__(self, sandbox: DockerSandbox | None = None) -> None:
        self.sandbox = sandbox or DockerSandbox()

    def verify(self, code: str, suite: TestSuite) -> VerificationResult:
        try:
            result = self.sandbox.execute(code, suite.model_dump())
        except SandboxUnavailableError as exc:
            return VerificationResult(success=False, message=str(exc))
        return VerificationResult(success=result.success, message=result.message)
