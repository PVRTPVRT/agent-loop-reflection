import json
from decimal import Decimal
from pathlib import Path

from agentloop.repository_benchmark import RepositoryBenchmarkDataset
from agentloop.repository_experiment import RepositoryExperimentReport

DATASET_PATH = Path("benchmarks/datasets/repository-v0.5.json")
REPORT_PATH = Path("benchmarks/results/repository-v0.5-mutation-matrix.json")


def test_repository_v0_5_adds_ttl_lru_without_losing_existing_tasks() -> None:
    dataset = RepositoryBenchmarkDataset.load(DATASET_PATH)

    assert dataset.dataset_id == "repository-v0.5"
    assert dataset.fingerprint == "df6d4daf95c28f9d"
    assert len(dataset.tasks) == 3
    assert {task.repository_id for task in dataset.tasks} == {
        "calculator-v1",
        "frame-decoder-v1",
        "ttl-lru-v1",
    }
    assert sum(len(task.mutations) for task in dataset.tasks) == 6


def test_repository_v0_5_mutation_report_matches_dataset_lineage() -> None:
    dataset = RepositoryBenchmarkDataset.load(DATASET_PATH)
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    assert report["dataset_id"] == dataset.dataset_id
    assert report["dataset_fingerprint"] == dataset.fingerprint
    assert report["all_matched"] is True
    assert len(report["results"]) == 6
    assert all(result["matched_expectation"] for result in report["results"])


def test_final_paired_api_report_matches_dataset_and_cost_accounting() -> None:
    dataset = RepositoryBenchmarkDataset.load(DATASET_PATH)
    report = RepositoryExperimentReport.model_validate_json(
        Path("benchmarks/results/repository-v0.5-api-pilot-r6.json").read_text(encoding="utf-8")
    )

    assert report.schema_version == "1.2"
    assert report.dataset_fingerprint == dataset.fingerprint
    assert report.paired_initial_candidates is True
    assert report.strategy_cost_accounting == "counterfactual_attribution"
    assert report.actual_cost_usd == Decimal("0.00525650")
    assert len(report.attempts) == 30
    assert [(aggregate.passed, aggregate.attempts) for aggregate in report.aggregates] == [
        (15, 15),
        (15, 15),
    ]
    for repetition in range(1, 6):
        for task in dataset.tasks:
            paired = [
                attempt
                for attempt in report.attempts
                if attempt.repetition == repetition and attempt.task_id == task.task_id
            ]
            assert len(paired) == 2
            assert paired[0].initial_patch_sha256 == paired[1].initial_patch_sha256
            assert paired[0].initial_patch is None
            assert paired[1].initial_patch is None


def test_r4_incident_preserves_one_successful_natural_repair() -> None:
    report = json.loads(
        Path("benchmarks/results/incidents/repository-v0.5-r4-repair-success.json").read_text(
            encoding="utf-8"
        )
    )
    repairs = [attempt for attempt in report["attempts"] if attempt["repair_triggered"]]

    assert len(repairs) == 1
    assert repairs[0]["task_id"] == "frame-decoder-repair-001"
    assert repairs[0]["initial_success"] is False
    assert repairs[0]["success"] is True
