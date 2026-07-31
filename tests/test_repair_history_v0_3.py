import pytest
from pydantic import ValidationError

from agentloop.evaluation_v2_models import (
    EvaluationCase,
    EvaluationDataset,
    EvaluationSuite,
)
from agentloop.repair_agents_v2 import render_repair_history
from agentloop.repair_v2 import RepairAttempt, RepairContext
from agentloop.repair_workflow_v2 import EvidenceDrivenRepairWorkflow
from agentloop.verifier import VerificationResult


class ForbiddenTester:
    def create_suite(self, task, *, critique=""):
        raise AssertionError("Repair mode must reuse routing evidence")


class RecordingCritic:
    def __init__(self) -> None:
        self.contexts = []

    def diagnose_repair(self, task, context):
        self.contexts.append(context)
        return f"hypothesis-{len(self.contexts)}"


class RecordingCoder:
    def __init__(self) -> None:
        self.contexts = []

    def repair_code(self, task, context, *, diagnosis, feedback=""):
        self.contexts.append(context)
        return f"def add(a, b):\n    return a + b  # attempt {len(self.contexts)}"


class FailOnceVerifier:
    def __init__(self) -> None:
        self.calls = 0

    def verify(self, code, suite):
        self.calls += 1
        return VerificationResult(
            success=self.calls == 2,
            message="passed route" if self.calls == 2 else "first repair still failed",
        )


def add_context() -> RepairContext:
    suite = EvaluationSuite(
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
    return RepairContext(
        task_id="add-001",
        failed_code="def add(a, b):\n    return a - b",
        routing_suite=suite,
        verification_message="initial route failure",
    )


def test_second_round_receives_original_and_failed_repair_history() -> None:
    task = EvaluationDataset.load("benchmarks/datasets/coding-v2-full.json").tasks[0]
    context = add_context()
    critic = RecordingCritic()
    coder = RecordingCoder()
    workflow = EvidenceDrivenRepairWorkflow(
        tester=ForbiddenTester(),
        critic=critic,
        coder=coder,
        verifier=FailOnceVerifier(),
        max_coding_rounds=2,
    )

    result = workflow.run(task, repair_context=context)

    assert result.success is True
    assert critic.contexts[0] is context
    assert critic.contexts[0].attempts == ()
    second_context = critic.contexts[1]
    assert [attempt.round_number for attempt in second_context.attempts] == [0, 1]
    assert [attempt.verification_message for attempt in second_context.attempts] == [
        "initial route failure",
        "first repair still failed",
    ]
    assert second_context.attempts[1].diagnosis == "hypothesis-1"
    assert coder.contexts[1] is second_context
    rendered = render_repair_history(second_context)
    assert "do not repeat" in rendered
    assert "initial route failure" in rendered
    assert "hypothesis-1" in rendered


def test_repair_attempt_rounds_must_be_unique_and_increasing() -> None:
    repeated = (
        RepairAttempt(
            round_number=1,
            diagnosis="first",
            verification_message="failed",
        ),
        RepairAttempt(
            round_number=1,
            diagnosis="duplicate",
            verification_message="failed again",
        ),
    )

    with pytest.raises(ValidationError, match="unique and increasing"):
        add_context().model_copy(update={"attempts": repeated}).model_validate(
            {
                **add_context().model_dump(),
                "attempts": [attempt.model_dump() for attempt in repeated],
            }
        )
