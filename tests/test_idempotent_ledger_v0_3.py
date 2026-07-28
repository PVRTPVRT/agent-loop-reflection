from copy import deepcopy

from hypothesis import given, settings
from hypothesis import strategies as st

from agentloop.contracts_v2 import ContractRegistryV2
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.oracles import oracle_process_idempotent_transfers
from agentloop.routing_suites import RoutingSuiteRegistry
from agentloop.suite_validation import validate_suite

ACCOUNTS = ("a", "b", "c", "d")


def event_sequences():
    return st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=10_000),
            st.sampled_from(ACCOUNTS),
            st.sampled_from(ACCOUNTS),
            st.integers(min_value=1, max_value=30),
        ).filter(lambda event: event[1] != event[2]),
        min_size=0,
        max_size=12,
        unique_by=lambda event: event[0],
    )


@given(
    st.fixed_dictionaries(
        {
            account: st.integers(min_value=0, max_value=100)
            for account in ACCOUNTS
        }
    ),
    event_sequences(),
)
@settings(max_examples=100, deadline=None, derandomize=True)
def test_duplicate_events_are_idempotent_and_conserve_balance(
    initial_balances,
    raw_events,
) -> None:
    events = [
        {
            "id": str(event_id),
            "from": source,
            "to": destination,
            "amount": amount,
        }
        for event_id, source, destination, amount in raw_events
    ]
    duplicated = [event for event in events for _ in range(2)]

    once = oracle_process_idempotent_transfers(initial_balances, events)
    twice = oracle_process_idempotent_transfers(initial_balances, duplicated)

    assert once["balances"] == twice["balances"]
    assert sum(once["balances"].values()) == sum(initial_balances.values())
    assert sum(twice["balances"].values()) == sum(initial_balances.values())
    assert twice["results"][::2] == once["results"]
    assert twice["results"][1::2] == once["results"]


def test_oracle_does_not_mutate_inputs() -> None:
    balances = {"a": 5, "b": 0}
    events = [{"id": "x", "from": "a", "to": "b", "amount": 2}]
    original_balances = deepcopy(balances)
    original_events = deepcopy(events)

    oracle_process_idempotent_transfers(balances, events)

    assert balances == original_balances
    assert events == original_events


def test_idempotent_ledger_assets_are_oracle_validated() -> None:
    dataset = EvaluationDataset.load(
        "benchmarks/datasets/coding-v3-idempotent-ledger-pilot.json"
    )
    routing = RoutingSuiteRegistry.load(
        "benchmarks/routing/coding-v3-idempotent-ledger-routing.json"
    )
    registry = ContractRegistryV2.load(
        "benchmarks/contracts/coding-v3-idempotent-ledger-contracts.json"
    )
    contract = registry.require("idempotent-ledger-001")

    assert validate_suite(dataset.tasks[0].evaluation_suite, contract)
    assert validate_suite(routing.require("idempotent-ledger-001"), contract)
