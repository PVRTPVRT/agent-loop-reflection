from agentloop.contracts_v2 import ContractRegistryV2
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.routing_suites import RoutingSuiteRegistry
from agentloop.suite_validation import validate_suite


def test_routing_suites_cover_full_dataset_and_match_contracts() -> None:
    hidden = EvaluationDataset.load("benchmarks/datasets/coding-v2-full.json")
    routing = RoutingSuiteRegistry.load()
    contracts = ContractRegistryV2.load("benchmarks/contracts/coding-v2-contracts.json")

    assert set(routing.suites) == {task.task_id for task in hidden.tasks}
    for task_id, suite in routing.suites.items():
        validate_suite(suite, contracts.require(task_id))


def test_routing_args_are_separate_from_hidden_args() -> None:
    hidden = EvaluationDataset.load("benchmarks/datasets/coding-v2-full.json")
    routing = RoutingSuiteRegistry.load()

    for task in hidden.tasks:
        hidden_args = {
            tuple(repr(value) for value in case.args) for case in task.evaluation_suite.test_cases
        }
        routing_args = {
            tuple(repr(value) for value in case.args)
            for case in routing.require(task.task_id).test_cases
        }
        assert hidden_args.isdisjoint(routing_args)
