from agentloop.contracts_v2 import ContractRegistryV2
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.suite_validation import validate_suite


def test_full_v2_dataset_has_eight_contract_valid_tasks() -> None:
    dataset = EvaluationDataset.load("benchmarks/datasets/coding-v2-full.json")
    registry = ContractRegistryV2.load("benchmarks/contracts/coding-v2-contracts.json")

    assert len(dataset.tasks) == 8
    assert {task.task_id for task in dataset.tasks} == set(registry.contracts)
    for task in dataset.tasks:
        validate_suite(
            task.evaluation_suite,
            registry.require(task.task_id),
        )
