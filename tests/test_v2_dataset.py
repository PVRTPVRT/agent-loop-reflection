from agentloop.contracts_v2 import ContractRegistryV2
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.suite_validation import validate_suite


def test_v2_pilot_hidden_suites_match_public_contracts() -> None:
    dataset = EvaluationDataset.load("benchmarks/datasets/coding-v2-pilot.json")
    registry = ContractRegistryV2.load("benchmarks/contracts/coding-v2-contracts.json")

    assert dataset.schema_version == "2.0"
    assert len(dataset.tasks) == 4
    for task in dataset.tasks:
        validate_suite(
            task.evaluation_suite,
            registry.require(task.task_id),
        )
