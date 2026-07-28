import pytest

from agentloop.evaluation_v2_models import EvaluationCase, EvaluationSuite
from agentloop.repair_v2 import RepairContext


def routing_suite() -> EvaluationSuite:
    return EvaluationSuite(
        function_name="add",
        test_cases=[
            EvaluationCase(
                args=[1, 2],
                expected=3,
                expected_exception=None,
                description="route evidence",
            )
        ],
    )


def test_repair_context_requires_failed_evidence() -> None:
    context = RepairContext(
        task_id="add-001",
        failed_code="def add(a, b):\n    return a - b",
        routing_suite=routing_suite(),
        verification_message="Case 1: expected 3, got -1",
    )

    assert context.routing_suite.function_name == "add"
    assert "expected 3" in context.verification_message


def test_repair_context_rejects_blank_code() -> None:
    with pytest.raises(ValueError, match="failed_code"):
        RepairContext(
            task_id="add-001",
            failed_code="   ",
            routing_suite=routing_suite(),
            verification_message="route failed",
        )
