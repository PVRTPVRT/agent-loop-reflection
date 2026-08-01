import json
from pathlib import Path

import pytest

from agentloop.repository_benchmark import (
    RepositoryBenchmarkDataset,
    RepositoryMutation,
    run_repository_mutation_matrix,
)
from agentloop.repository_verifier import RepositoryFixtureError
from agentloop.sandbox import ExecutionResult

DATASET_PATH = Path("benchmarks/datasets/repository-v0.4.json")


class UnexpectedRunner:
    def execute_workspace(self, *args, **kwargs) -> ExecutionResult:
        raise AssertionError("runner must not execute for stale dataset metadata")


def test_repository_dataset_is_versioned_and_covers_easy_and_hard_tasks() -> None:
    first = RepositoryBenchmarkDataset.load(DATASET_PATH)
    second = RepositoryBenchmarkDataset.load(DATASET_PATH)

    assert first.schema_version == "1.0"
    assert first.dataset_id == "repository-v0.4"
    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 16
    assert {task.difficulty for task in first.tasks} == {"easy", "hard"}
    assert sum(len(task.mutations) for task in first.tasks) == 4


def test_committed_mutation_report_matches_dataset_lineage() -> None:
    dataset = RepositoryBenchmarkDataset.load(DATASET_PATH)
    report = json.loads(
        Path("benchmarks/results/repository-v0.4-mutation-matrix.json").read_text(encoding="utf-8")
    )

    assert report["dataset_id"] == dataset.dataset_id
    assert report["dataset_fingerprint"] == dataset.fingerprint
    assert report["all_matched"] is True
    assert all(result["matched_expectation"] for result in report["results"])


def test_repository_dataset_rejects_patch_path_escape() -> None:
    with pytest.raises(ValueError, match="project root"):
        RepositoryMutation(
            mutation_id="escape",
            patch_path="../outside.patch",
            expected_success=False,
        )


def test_mutation_matrix_rejects_stale_fixture_before_execution() -> None:
    dataset = RepositoryBenchmarkDataset.load(DATASET_PATH)
    stale_task = dataset.tasks[0].model_copy(update={"fixture_revision": "0" * 64})
    stale_dataset = dataset.model_copy(update={"tasks": (stale_task, *dataset.tasks[1:])})

    with pytest.raises(RepositoryFixtureError, match="revision is stale"):
        run_repository_mutation_matrix(
            stale_dataset,
            project_root=Path.cwd(),
            runner=UnexpectedRunner(),
        )
