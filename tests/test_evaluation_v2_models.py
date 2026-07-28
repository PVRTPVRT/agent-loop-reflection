import pytest
from pydantic import ValidationError

from agentloop.evaluation_v2_models import EvaluationCase, EvaluationSuite


def test_expected_exception_case_is_valid() -> None:
    case = EvaluationCase(
        args=[-1],
        expected=None,
        expected_exception="ValueError",
        description="negative",
    )

    assert case.expected_exception == "ValueError"


def test_value_and_exception_cannot_both_be_expected() -> None:
    with pytest.raises(ValidationError, match="expected must be null"):
        EvaluationCase(
            args=[-1],
            expected=1,
            expected_exception="ValueError",
            description="invalid",
        )


def test_duplicate_args_are_rejected() -> None:
    case = {
        "args": [1],
        "expected": 1,
        "expected_exception": None,
        "description": "same",
    }
    with pytest.raises(ValidationError, match="duplicate args"):
        EvaluationSuite(
            function_name="identity",
            test_cases=[case, case],
        )
