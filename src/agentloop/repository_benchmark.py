"""Versioned, zero-API mutation matrix for trusted repository fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from agentloop.evaluation_boundary import RepositoryPatchArtifact, TestCommandSpec
from agentloop.repository_verifier import (
    RepositoryFixture,
    RepositoryFixtureError,
    RepositoryFixtureRegistry,
    RepositoryWorkspaceVerifier,
    WorkspaceRunner,
)


def _relative_project_path(value: str, field_name: str) -> str:
    path = PurePosixPath(value)
    if "\\" in value or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field_name} must stay inside the project root")
    return path.as_posix()


class RepositoryBenchmarkModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RepositoryMutation(RepositoryBenchmarkModel):
    mutation_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    patch_path: str = Field(min_length=1)
    expected_success: bool

    @field_validator("patch_path")
    @classmethod
    def require_relative_patch_path(cls, value: str) -> str:
        return _relative_project_path(value, "patch_path")


class RepositoryBenchmarkTask(RepositoryBenchmarkModel):
    task_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    category: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    prompt: str = Field(min_length=1)
    repository_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    fixture_path: str = Field(min_length=1)
    fixture_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    protected_paths: tuple[str, ...] = Field(min_length=1)
    evaluation: TestCommandSpec
    mutations: tuple[RepositoryMutation, ...] = Field(min_length=2)

    @field_validator("fixture_path")
    @classmethod
    def require_relative_fixture_path(cls, value: str) -> str:
        return _relative_project_path(value, "fixture_path")

    @field_validator("protected_paths")
    @classmethod
    def require_relative_protected_paths(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_relative_project_path(value, "protected_path") for value in values)

    @model_validator(mode="after")
    def require_unique_mutation_ids(self) -> RepositoryBenchmarkTask:
        identifiers = [mutation.mutation_id for mutation in self.mutations]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("mutation_id values must be unique within a task")
        return self


class RepositoryBenchmarkDataset(RepositoryBenchmarkModel):
    schema_version: Literal["1.0"]
    dataset_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    tasks: tuple[RepositoryBenchmarkTask, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_task_ids(self) -> RepositoryBenchmarkDataset:
        identifiers = [task.task_id for task in self.tasks]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("repository benchmark task_id values must be unique")
        return self

    @property
    def fingerprint(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def load(cls, path: str | Path) -> RepositoryBenchmarkDataset:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))


class RepositoryMutationResult(RepositoryBenchmarkModel):
    task_id: str
    mutation_id: str
    expected_success: bool
    observed_success: bool
    matched_expectation: bool
    message: str


class RepositoryMutationReport(RepositoryBenchmarkModel):
    dataset_id: str
    dataset_fingerprint: str
    results: tuple[RepositoryMutationResult, ...] = Field(min_length=1)

    @computed_field
    @property
    def all_matched(self) -> bool:
        return all(result.matched_expectation for result in self.results)


def _project_path(project_root: Path, relative: str) -> Path:
    root = project_root.resolve()
    candidate = root.joinpath(*PurePosixPath(relative).parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RepositoryFixtureError(f"benchmark path escapes project root: {relative}") from exc
    return candidate


def run_repository_mutation_matrix(
    dataset: RepositoryBenchmarkDataset,
    *,
    project_root: Path,
    runner: WorkspaceRunner,
) -> RepositoryMutationReport:
    """Execute registered patches without calling an LLM."""
    results = []
    for task in dataset.tasks:
        fixture = RepositoryFixture.load(
            task.repository_id,
            _project_path(project_root, task.fixture_path),
            protected_paths=task.protected_paths,
        )
        if fixture.revision != task.fixture_revision:
            raise RepositoryFixtureError(
                f"dataset fixture revision is stale for {task.repository_id}: "
                f"expected {task.fixture_revision}, got {fixture.revision}"
            )
        verifier = RepositoryWorkspaceVerifier(
            runner=runner,
            fixtures=RepositoryFixtureRegistry([fixture]),
        )
        for mutation in task.mutations:
            patch = _project_path(project_root, mutation.patch_path).read_text(encoding="utf-8")
            observed = verifier.verify_artifact(
                RepositoryPatchArtifact(
                    repository_id=fixture.repository_id,
                    base_revision=fixture.revision,
                    patch=patch,
                ),
                task.evaluation,
            )
            results.append(
                RepositoryMutationResult(
                    task_id=task.task_id,
                    mutation_id=mutation.mutation_id,
                    expected_success=mutation.expected_success,
                    observed_success=observed.success,
                    matched_expectation=observed.success == mutation.expected_success,
                    message=observed.message,
                )
            )
    return RepositoryMutationReport(
        dataset_id=dataset.dataset_id,
        dataset_fingerprint=dataset.fingerprint,
        results=tuple(results),
    )
