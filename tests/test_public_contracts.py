from pathlib import Path

import pytest

from agentloop.public_contracts import ContractRegistry, contract_prompt

CONTRACT_PATH = Path("benchmarks/contracts/coding-v1-contracts.json")


def test_contract_registry_covers_all_benchmark_tasks() -> None:
    from agentloop.benchmark_models import BenchmarkDataset

    dataset = BenchmarkDataset.load("benchmarks/datasets/coding-v1.json")
    registry = ContractRegistry.load(CONTRACT_PATH)

    assert set(registry.contracts) == {task.task_id for task in dataset.tasks}
    assert registry.dataset_id == dataset.dataset_id


def test_add_contract_exposes_domain_without_hidden_values() -> None:
    registry = ContractRegistry.load(CONTRACT_PATH)
    rendered = contract_prompt(registry.require("add-001"))

    assert "integer or finite float" in rendered
    assert "1.5" not in rendered
    assert "2.25" not in rendered


def test_missing_contract_fails_closed() -> None:
    registry = ContractRegistry.load(CONTRACT_PATH)

    with pytest.raises(ValueError, match="No public contract"):
        registry.require("unknown-task")
