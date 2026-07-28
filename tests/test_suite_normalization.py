from agentloop.contracts_v2 import ContractRegistryV2
from agentloop.evaluation_v2_models import EvaluationCase, EvaluationSuite
from agentloop.suite_normalization import normalize_suite

REGISTRY = ContractRegistryV2.load("benchmarks/contracts/coding-v2-contracts.json")


def test_normalizer_corrects_python_equality_outcome() -> None:
    raw = EvaluationSuite(
        function_name="deduplicate",
        test_cases=[
            EvaluationCase(
                args=[[0, False, 1, True, 2]],
                expected=[0, False, 1, True, 2],
                expected_exception=None,
                description="mixed equality",
            )
        ],
    )

    normalized = normalize_suite(raw, REGISTRY.require("deduplicate-001"))

    assert normalized.suite.test_cases[0].expected == [0, 1, 2]
    assert normalized.corrections


def test_normalizer_drops_unhashable_cases() -> None:
    raw = EvaluationSuite(
        function_name="deduplicate",
        test_cases=[
            EvaluationCase(
                args=[[[1], [1]]],
                expected=[[1]],
                expected_exception=None,
                description="outside domain",
            ),
            EvaluationCase(
                args=[[1, 1, 2]],
                expected=[1, 2],
                expected_exception=None,
                description="valid",
            ),
        ],
    )

    normalized = normalize_suite(raw, REGISTRY.require("deduplicate-001"))

    assert len(normalized.suite.test_cases) == 1
    assert "dropped case 1" in normalized.corrections[0]


def test_normalizer_sets_required_exception() -> None:
    raw = EvaluationSuite(
        function_name="factorial",
        test_cases=[
            EvaluationCase(
                args=[-1],
                expected=None,
                expected_exception=None,
                description="negative",
            )
        ],
    )

    normalized = normalize_suite(raw, REGISTRY.require("factorial-001"))

    assert normalized.suite.test_cases[0].expected_exception == "ValueError"
