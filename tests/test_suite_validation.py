import pytest

from agentloop.contracts_v2 import ContractRegistryV2
from agentloop.evaluation_v2_models import EvaluationCase, EvaluationSuite
from agentloop.suite_validation import SuiteContractError, validate_suite

REGISTRY = ContractRegistryV2.load("benchmarks/contracts/coding-v2-contracts.json")


def suite(function_name, cases):
    return EvaluationSuite(function_name=function_name, test_cases=cases)


def test_factorial_expected_exception_is_validated() -> None:
    generated = suite(
        "factorial",
        [
            EvaluationCase(
                args=[-1],
                expected=None,
                expected_exception="ValueError",
                description="negative",
            )
        ],
    )

    assert validate_suite(generated, REGISTRY.require("factorial-001")) == generated


def test_factorial_placeholder_expected_is_rejected() -> None:
    generated = suite(
        "factorial",
        [
            EvaluationCase(
                args=[10],
                expected="__LARGE_INTEGER__",
                expected_exception=None,
                description="placeholder",
            )
        ],
    )

    with pytest.raises(SuiteContractError, match="trusted outcome"):
        validate_suite(generated, REGISTRY.require("factorial-001"))


def test_deduplicate_unhashable_item_is_rejected() -> None:
    generated = suite(
        "deduplicate",
        [
            EvaluationCase(
                args=[[[1, 2], [1, 2]]],
                expected=[[1, 2]],
                expected_exception=None,
                description="invalid domain",
            )
        ],
    )

    with pytest.raises(SuiteContractError, match="unhashable"):
        validate_suite(generated, REGISTRY.require("deduplicate-001"))


def test_deduplicate_python_equality_is_enforced() -> None:
    generated = suite(
        "deduplicate",
        [
            EvaluationCase(
                args=[[0, False, 1, True, 2]],
                expected=[0, 1, True, 2],
                expected_exception=None,
                description="wrong equality",
            )
        ],
    )

    with pytest.raises(SuiteContractError, match="trusted outcome"):
        validate_suite(generated, REGISTRY.require("deduplicate-001"))
