from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from agentloop.evaluation_boundary import (
    FunctionCaseSpec,
    RepositoryPatchArtifact,
    SourceCodeArtifact,
    UnsupportedEvaluationBoundaryError,
)
from agentloop.evaluation_boundary import (
    TestCommandSpec as CommandSpec,
)
from agentloop.evaluation_v2_models import EvaluationCase, EvaluationSuite
from agentloop.repository_verifier import (
    RepositoryFixture,
    RepositoryFixtureRegistry,
    RepositoryWorkspaceVerifier,
    repository_fingerprint,
)
from agentloop.sandbox import ExecutionResult

FIXTURE_ROOT = Path("benchmarks/repositories/calculator-v1")
FIX_PATCH = Path("benchmarks/fixtures/repository-calculator-fix.patch")


class InspectingRunner:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute_workspace(
        self,
        workspace: Path,
        *,
        command: Sequence[str],
        working_directory: str,
        timeout_seconds: int,
        read_only: bool,
    ) -> ExecutionResult:
        code = (workspace / "calculator.py").read_text(encoding="utf-8")
        self.calls.append(
            {
                "code": code,
                "command": tuple(command),
                "working_directory": working_directory,
                "timeout_seconds": timeout_seconds,
                "read_only": read_only,
            }
        )
        success = "return a + b" in code
        return ExecutionResult(
            success=success,
            message="repository tests passed" if success else "repository tests failed",
        )


def build_verifier() -> tuple[
    RepositoryWorkspaceVerifier,
    RepositoryFixture,
    InspectingRunner,
]:
    fixture = RepositoryFixture.load(
        "calculator-v1",
        FIXTURE_ROOT,
        protected_paths=("test_calculator.py",),
    )
    runner = InspectingRunner()
    verifier = RepositoryWorkspaceVerifier(
        runner=runner,
        fixtures=RepositoryFixtureRegistry([fixture]),
    )
    return verifier, fixture, runner


def patch_artifact(
    fixture: RepositoryFixture,
    *,
    patch: str | None = None,
) -> RepositoryPatchArtifact:
    return RepositoryPatchArtifact(
        repository_id=fixture.repository_id,
        base_revision=fixture.revision,
        patch=patch or FIX_PATCH.read_text(encoding="utf-8"),
    )


def command_spec() -> CommandSpec:
    return CommandSpec(
        command=("python", "-B", "-m", "unittest", "-q"),
        timeout_seconds=20,
    )


def test_repository_fixture_requires_protected_tests() -> None:
    with pytest.raises(ValueError, match="protected test path"):
        RepositoryFixture.load("calculator-v1", FIXTURE_ROOT)

def test_repository_fingerprint_is_stable_and_content_sensitive(tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (second / "module.py").write_text("VALUE = 1\n", encoding="utf-8")

    assert repository_fingerprint(first) == repository_fingerprint(second)

    (second / "module.py").write_text("VALUE = 2\n", encoding="utf-8")
    assert repository_fingerprint(first) != repository_fingerprint(second)


def test_repository_verifier_applies_patch_to_disposable_copy() -> None:
    verifier, fixture, runner = build_verifier()
    original = (fixture.root / "calculator.py").read_text(encoding="utf-8")

    result = verifier.verify_artifact(patch_artifact(fixture), command_spec())

    assert result.success is True
    assert runner.calls == [
        {
            "code": original.replace("return a - b", "return a + b"),
            "command": ("python", "-B", "-m", "unittest", "-q"),
            "working_directory": ".",
            "timeout_seconds": 20,
            "read_only": True,
        }
    ]
    assert (fixture.root / "calculator.py").read_text(encoding="utf-8") == original


def test_repository_verifier_rejects_revision_mismatch_before_execution() -> None:
    verifier, fixture, runner = build_verifier()
    artifact = patch_artifact(fixture).model_copy(
        update={"base_revision": "wrong-revision"}
    )

    result = verifier.verify_artifact(artifact, command_spec())

    assert result.success is False
    assert "revision mismatch" in result.message
    assert runner.calls == []


def test_repository_verifier_rejects_path_traversal_before_git_apply() -> None:
    verifier, fixture, runner = build_verifier()
    unsafe_patch = """diff --git a/../outside.py b/../outside.py
--- a/../outside.py
+++ b/../outside.py
@@ -0,0 +1 @@
+owned = True
"""

    result = verifier.verify_artifact(
        patch_artifact(fixture, patch=unsafe_patch),
        command_spec(),
    )

    assert result.success is False
    assert "unsafe repository path" in result.message
    assert runner.calls == []


def test_repository_verifier_rejects_protected_test_change() -> None:
    verifier, fixture, runner = build_verifier()
    test_tampering_patch = """diff --git a/test_calculator.py b/test_calculator.py
--- a/test_calculator.py
+++ b/test_calculator.py
@@ -6,1 +6,1 @@
-class CalculatorTests(unittest.TestCase):
+class DisabledCalculatorTests(unittest.TestCase):
"""

    result = verifier.verify_artifact(
        patch_artifact(fixture, patch=test_tampering_patch),
        command_spec(),
    )

    assert result.success is False
    assert "protected fixture paths: test_calculator.py" in result.message
    assert runner.calls == []


def test_repository_verifier_rejects_wrong_boundary_pair() -> None:
    verifier, _, _ = build_verifier()
    suite = EvaluationSuite(
        function_name="identity",
        test_cases=[
            EvaluationCase(
                args=[1],
                expected=1,
                expected_exception=None,
                description="identity",
            )
        ],
    )

    with pytest.raises(UnsupportedEvaluationBoundaryError, match="source_code"):
        verifier.verify_artifact(
            SourceCodeArtifact(content="def identity(value): return value"),
            FunctionCaseSpec(suite=suite),
        )
