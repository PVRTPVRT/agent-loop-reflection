"""Managed verifier for typed V2 function cases."""

from __future__ import annotations

from typing import Any, Protocol

from agentloop.evaluation_boundary import (
    CandidateArtifact,
    EvaluationSpec,
    require_function_suite,
    require_source_code,
)
from agentloop.evaluation_v2_models import EvaluationSuite
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2
from agentloop.sandbox import ExecutionResult, SandboxUnavailableError
from agentloop.telemetry import traced_verification_method
from agentloop.verifier import VerificationResult


class EvaluationSandbox(Protocol):
    def execute_v2(
        self,
        code: str,
        test_suite: dict[str, Any],
    ) -> ExecutionResult:
        """Execute one function candidate against typed cases."""


class EvaluationCodeVerifier:
    def __init__(self, sandbox: EvaluationSandbox | None = None) -> None:
        self.sandbox = sandbox or ManagedDockerSandboxV2()

    @traced_verification_method()
    def verify(
        self,
        code: str,
        suite: EvaluationSuite,
    ) -> VerificationResult:
        try:
            result = self.sandbox.execute_v2(code, suite.model_dump(mode="json"))
        except SandboxUnavailableError as exc:
            return VerificationResult(success=False, message=str(exc))
        return VerificationResult(success=result.success, message=result.message)

    def verify_artifact(
        self,
        artifact: CandidateArtifact,
        spec: EvaluationSpec,
    ) -> VerificationResult:
        """Bridge the generic boundary to the function-case sandbox."""
        return self.verify(
            require_source_code(artifact),
            require_function_suite(spec),
        )
