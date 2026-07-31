"""Docker verifier for V2 value and expected-exception assertions."""

from __future__ import annotations

from agentloop.evaluation_boundary import (
    CandidateArtifact,
    EvaluationSpec,
    require_function_suite,
    require_source_code,
)
from agentloop.evaluation_v2_models import EvaluationSuite
from agentloop.sandbox import DockerSandbox, SandboxUnavailableError
from agentloop.telemetry import traced_verification_method
from agentloop.verifier import VerificationResult


class EvaluationCodeVerifier:
    def __init__(self, sandbox: DockerSandbox | None = None) -> None:
        self.sandbox = sandbox or DockerSandbox()

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
        """Bridge the generic boundary to the existing function-case sandbox."""
        return self.verify(
            require_source_code(artifact),
            require_function_suite(spec),
        )
