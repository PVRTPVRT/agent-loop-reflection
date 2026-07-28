import pytest

from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.oracles import oracle_simulate_ttl_lru


def test_r2_hidden_cases_match_trusted_oracle() -> None:
    dataset = EvaluationDataset.load(
        "benchmarks/datasets/coding-v2-repair-pilot-r2.json"
    )

    for case in dataset.tasks[0].evaluation_suite.test_cases:
        capacity, events = case.args
        if case.expected_exception:
            with pytest.raises(ValueError):
                oracle_simulate_ttl_lru(capacity, events)
        else:
            assert oracle_simulate_ttl_lru(capacity, events) == case.expected
