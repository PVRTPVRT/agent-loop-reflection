from pathlib import Path

from agentloop.benchmark_models import BenchmarkDataset
from agentloop.public_contracts import ContractRegistry

PILOT_PATH = Path("benchmarks/datasets/coding-v1-pilot.json")


def test_pilot_has_four_representative_paired_tasks() -> None:
    dataset = BenchmarkDataset.load(PILOT_PATH)

    assert len(dataset.tasks) == 4
    assert {task.category for task in dataset.tasks} == {
        "arithmetic",
        "string",
        "collection",
    }
    assert {task.difficulty for task in dataset.tasks} == {"easy", "medium"}


def test_every_pilot_task_has_a_public_contract() -> None:
    dataset = BenchmarkDataset.load(PILOT_PATH)
    registry = ContractRegistry.load("benchmarks/contracts/coding-v1-contracts.json")

    for task in dataset.tasks:
        assert registry.require(task.task_id).function_name == (task.evaluation_suite.function_name)
