from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from agentloop.evaluation_boundary import (
    FunctionCaseSpec,
    RepositoryPatchArtifact,
    SourceCodeArtifact,
    UnsupportedEvaluationBoundaryError,
    verify_artifact,
)
from agentloop.evaluation_boundary import (
    TestCommandSpec as CommandSpec,
)
from agentloop.evaluation_v2_models import EvaluationCase, EvaluationSuite
from agentloop.evaluation_verifier import EvaluationCodeVerifier
from agentloop.repair_v2 import RepairContext
from agentloop.sandbox import ExecutionResult
from agentloop.verifier import VerificationResult


def routing_suite() -> EvaluationSuite:
    return EvaluationSuite(
        function_name="add",
        test_cases=[
            EvaluationCase(
                args=[1, 2],
                expected=3,
                expected_exception=None,
                description="route evidence",
            )
        ],
    )


class LegacyVerifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, EvaluationSuite]] = []

    def verify(self, code: str, suite: EvaluationSuite) -> VerificationResult:
        self.calls.append((code, suite))
        return VerificationResult(success=True, message="legacy passed")


class GenericVerifier:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, Any]] = []

    def verify_artifact(self, artifact: Any, spec: Any) -> VerificationResult:
        self.calls.append((artifact, spec))
        return VerificationResult(success=True, message="generic passed")


class PassingSandbox:
    def execute_v2(self, code: str, test_suite: dict[str, Any]) -> ExecutionResult:
        assert code.startswith("def add")
        assert test_suite["function_name"] == "add"
        return ExecutionResult(success=True, message="sandbox passed")


def test_legacy_verifier_is_adapted_at_the_boundary() -> None:
    verifier = LegacyVerifier()
    artifact = SourceCodeArtifact(content="def add(a, b):\n    return a + b")
    spec = FunctionCaseSpec(suite=routing_suite())

    result = verify_artifact(verifier, artifact, spec)

    assert result.success
    assert verifier.calls == [(artifact.content, spec.suite)]


def test_generic_verifier_is_preferred_without_legacy_method() -> None:
    verifier = GenericVerifier()
    artifact = SourceCodeArtifact(content="def add(a, b):\n    return a + b")
    spec = FunctionCaseSpec(suite=routing_suite())

    result = verify_artifact(verifier, artifact, spec)

    assert result.message == "generic passed"
    assert verifier.calls == [(artifact, spec)]


def test_evaluation_code_verifier_bridges_typed_function_boundary() -> None:
    verifier = EvaluationCodeVerifier(sandbox=PassingSandbox())

    result = verifier.verify_artifact(
        SourceCodeArtifact(content="def add(a, b):\n    return a + b"),
        FunctionCaseSpec(suite=routing_suite()),
    )

    assert result == VerificationResult(success=True, message="sandbox passed")


def test_unsupported_artifact_spec_pair_fails_explicitly() -> None:
    with pytest.raises(UnsupportedEvaluationBoundaryError, match="repository_patch"):
        verify_artifact(
            LegacyVerifier(),
            RepositoryPatchArtifact(
                repository_id="sample-repo",
                base_revision="abc123",
                patch="--- a/app.py\n+++ b/app.py",
            ),
            FunctionCaseSpec(suite=routing_suite()),
        )


@pytest.mark.parametrize(
    "working_directory",
    ["", "   ", "/tmp/project", r"C:\temp\project", "C:project", "../project"],
)
def test_test_command_spec_rejects_workspace_escape(
    working_directory: str,
) -> None:
    with pytest.raises(ValidationError, match="working_directory"):
        CommandSpec(
            command=("python", "-m", "pytest"),
            working_directory=working_directory,
        )


def test_test_command_spec_is_safe_by_construction() -> None:
    spec = CommandSpec(
        command=("python", "-m", "pytest", "-q"),
        working_directory="tests/integration",
        timeout_seconds=120,
    )

    assert spec.network_enabled is False
    with pytest.raises(ValidationError):
        CommandSpec(command=("pytest",), network_enabled=True)
    with pytest.raises(ValidationError, match="tokens"):
        CommandSpec(command=("python", " "))


def test_repair_context_accepts_legacy_and_typed_inputs_without_duplicate_state() -> None:
    suite = routing_suite()
    code = "def add(a, b):\n    return a - b"
    legacy = RepairContext(
        task_id="add-001",
        failed_code=code,
        routing_suite=suite,
        verification_message="expected 3, got -1",
    )
    typed = RepairContext(
        task_id="add-001",
        candidate_artifact=SourceCodeArtifact(content=code),
        evaluation_spec=FunctionCaseSpec(suite=suite),
        verification_message="expected 3, got -1",
    )

    assert legacy == typed
    assert typed.failed_code == code
    assert typed.routing_suite == suite
    assert set(typed.model_dump()) == {
        "task_id",
        "candidate_artifact",
        "evaluation_spec",
        "verification_message",
        "attempts",
    }


def test_repair_context_can_carry_future_repository_evidence() -> None:
    context = RepairContext(
        task_id="repo-001",
        candidate_artifact=RepositoryPatchArtifact(
            repository_id="sample-repo",
            patch="--- a/app.py\n+++ b/app.py",
            base_revision="abc123",
        ),
        evaluation_spec=CommandSpec(command=("python", "-m", "pytest", "-q")),
        verification_message="one repository test failed",
    )

    assert context.candidate_artifact.kind == "repository_patch"
    assert context.evaluation_spec.kind == "test_command"
    with pytest.raises(UnsupportedEvaluationBoundaryError, match="repository_patch"):
        _ = context.failed_code
    with pytest.raises(UnsupportedEvaluationBoundaryError, match="test_command"):
        _ = context.routing_suite


def test_repair_context_rejects_duplicate_legacy_and_typed_fields() -> None:
    with pytest.raises(ValidationError, match="not both"):
        RepairContext(
            task_id="add-001",
            failed_code="def add(a, b): return a - b",
            candidate_artifact=SourceCodeArtifact(
                content="def add(a, b): return a - b"
            ),
            routing_suite=routing_suite(),
            verification_message="route failed",
        )
