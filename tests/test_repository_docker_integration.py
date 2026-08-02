from pathlib import Path

import pytest

from agentloop.evaluation_boundary import (
    RepositoryPatchArtifact,
)
from agentloop.evaluation_boundary import (
    TestCommandSpec as CommandSpec,
)
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2
from agentloop.repository_benchmark import (
    RepositoryBenchmarkDataset,
    run_repository_mutation_matrix,
)
from agentloop.repository_verifier import (
    RepositoryFixture,
    RepositoryFixtureRegistry,
    RepositoryWorkspaceVerifier,
)

FIXTURE_ROOT = Path("benchmarks/repositories/calculator-v1")


def build_verifier() -> tuple[RepositoryWorkspaceVerifier, RepositoryFixture]:
    runner = ManagedDockerSandboxV2(timeout_seconds=20)
    if not runner.is_available():
        pytest.skip("Docker Engine is unavailable")
    fixture = RepositoryFixture.load(
        "calculator-v1",
        FIXTURE_ROOT,
        protected_paths=("test_calculator.py",),
    )
    return (
        RepositoryWorkspaceVerifier(
            runner=runner,
            fixtures=RepositoryFixtureRegistry([fixture]),
        ),
        fixture,
    )


def artifact(fixture: RepositoryFixture, patch_path: str) -> RepositoryPatchArtifact:
    return RepositoryPatchArtifact(
        repository_id=fixture.repository_id,
        base_revision=fixture.revision,
        patch=Path(patch_path).read_text(encoding="utf-8"),
    )


def test_repository_patch_repairs_fixture_in_managed_docker() -> None:
    verifier, fixture = build_verifier()

    result = verifier.verify_artifact(
        artifact(fixture, "benchmarks/fixtures/repository-calculator-fix.patch"),
        CommandSpec(command=("python", "-B", "-m", "unittest", "-q")),
    )

    assert result.success is True


def test_repository_non_fix_remains_failed_in_managed_docker() -> None:
    verifier, fixture = build_verifier()

    result = verifier.verify_artifact(
        artifact(fixture, "benchmarks/fixtures/repository-calculator-non-fix.patch"),
        CommandSpec(command=("python", "-B", "-m", "unittest", "-q")),
    )

    assert result.success is False
    assert "FAILED" in result.message


def test_versioned_repository_mutation_matrix_matches_all_expectations() -> None:
    runner = ManagedDockerSandboxV2(timeout_seconds=20)
    if not runner.is_available():
        pytest.skip("Docker Engine is unavailable")

    report = run_repository_mutation_matrix(
        RepositoryBenchmarkDataset.load("benchmarks/datasets/repository-v0.5.json"),
        project_root=Path.cwd(),
        runner=runner,
    )

    assert report.all_matched is True
    assert [result.observed_success for result in report.results] == [
        True,
        False,
        True,
        False,
        True,
        False,
    ]
