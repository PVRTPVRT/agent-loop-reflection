import pytest

from agentloop.contracts_v2 import ContractRegistryV2
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.oracles import oracle_simulate_ttl_lru
from agentloop.routing_suites import RoutingSuiteRegistry


def test_ttl_lru_oracle_handles_expiry_before_eviction() -> None:
    events = [
        {"op": "put", "key": "a", "value": "A", "ttl": 2, "time": 0},
        {"op": "put", "key": "b", "value": "B", "ttl": 10, "time": 0},
        {"op": "get", "key": "a", "time": 1},
        {"op": "put", "key": "c", "value": "C", "ttl": 10, "time": 2},
        {"op": "get", "key": "a", "time": 2},
        {"op": "get", "key": "b", "time": 2},
        {"op": "get", "key": "c", "time": 2},
    ]

    assert oracle_simulate_ttl_lru(2, events) == ["A", None, "B", "C"]


def test_ttl_lru_oracle_rejects_invalid_capacity() -> None:
    with pytest.raises(ValueError, match="capacity"):
        oracle_simulate_ttl_lru(-1, [])


def test_v0_2_pilot_assets_share_task_identity() -> None:
    dataset = EvaluationDataset.load("benchmarks/datasets/coding-v2-repair-pilot.json")
    routing = RoutingSuiteRegistry.load("benchmarks/routing/coding-v2-repair-routing.json")
    contracts = ContractRegistryV2.load(
        "benchmarks/contracts/coding-v2-repair-contracts.json"
    )

    assert dataset.tasks[0].task_id == "ttl-lru-001"
    assert routing.require("ttl-lru-001").function_name == "simulate_ttl_lru"
    assert contracts.require("ttl-lru-001").oracle == "simulate_ttl_lru"
