import pytest

from agentloop.contracts_v2 import ContractRegistryV2
from agentloop.evaluation_v2_models import (
    EvaluationCase,
    EvaluationDataset,
    EvaluationSuite,
)
from agentloop.suite_validation import SuiteContractError, validate_suite


def registry() -> ContractRegistryV2:
    return ContractRegistryV2.load(
        "benchmarks/contracts/coding-v3-frame-decoder-contracts.json"
    )


def test_frame_decoder_hidden_suite_is_oracle_validated() -> None:
    dataset = EvaluationDataset.load(
        "benchmarks/datasets/coding-v3-frame-decoder-pilot.json"
    )

    validated = validate_suite(
        dataset.tasks[0].evaluation_suite,
        registry().require("frame-decoder-001"),
    )

    assert validated is dataset.tasks[0].evaluation_suite


def test_dynamic_exception_requires_the_oracle_exception_type() -> None:
    suite = EvaluationSuite(
        function_name="decode_frames_by_chunk",
        test_cases=[
            EvaluationCase(
                args=[["not-hex"], 8],
                expected=None,
                expected_exception=None,
                description="invalid hex without expected exception",
            )
        ],
    )

    with pytest.raises(SuiteContractError, match="must be 'ValueError'"):
        validate_suite(suite, registry().require("frame-decoder-001"))


def test_dynamic_exception_is_rejected_when_oracle_returns() -> None:
    suite = EvaluationSuite(
        function_name="decode_frames_by_chunk",
        test_cases=[
            EvaluationCase(
                args=[["00000000"], 0],
                expected=None,
                expected_exception="ValueError",
                description="valid zero-length frame",
            )
        ],
    )

    with pytest.raises(SuiteContractError, match="must be None"):
        validate_suite(suite, registry().require("frame-decoder-001"))
