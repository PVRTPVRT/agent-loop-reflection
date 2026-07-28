from agentloop.evaluation_v2_models import (
    EvaluationCase,
    EvaluationDataset,
    EvaluationSuite,
)
from agentloop.repair_v2 import RepairContext
from agentloop.repair_workflow_v2 import EvidenceDrivenRepairWorkflow
from agentloop.verifier import VerificationResult


class ForbiddenTester:
    def __init__(self) -> None:
        self.normalization_history = []

    def create_suite(self, task, *, critique=""):
        raise AssertionError("Repair mode must reuse the pre-registered routing suite")


class RecordingCritic:
    def __init__(self) -> None:
        self.context = None

    def diagnose_repair(self, task, context):
        self.context = context
        return "The candidate subtracts instead of adding."


class RecordingCoder:
    def __init__(self) -> None:
        self.context = None
        self.diagnosis = ""

    def repair_code(self, task, context, *, diagnosis, feedback=""):
        self.context = context
        self.diagnosis = diagnosis
        return "def add(a, b):\n    return a + b"


class AddVerifier:
    def verify(self, code, suite):
        success = "return a + b" in code
        return VerificationResult(
            success=success,
            message="passed repair route" if success else "route still failing",
        )


def test_repair_workflow_reuses_failure_evidence() -> None:
    task = EvaluationDataset.load("benchmarks/datasets/coding-v2-full.json").tasks[0]
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
    context = RepairContext(
        task_id=task.task_id,
        failed_code="def add(a, b):\n    return a - b",
        routing_suite=suite,
        verification_message="Case 1: expected 3, got -1",
    )
    critic = RecordingCritic()
    coder = RecordingCoder()
    workflow = EvidenceDrivenRepairWorkflow(
        tester=ForbiddenTester(),
        critic=critic,
        coder=coder,
        verifier=AddVerifier(),
        max_coding_rounds=2,
    )

    result = workflow.run(task, repair_context=context)

    assert result.success is True
    assert result.code == "def add(a, b):\n    return a + b"
    assert critic.context is context
    assert coder.context is context
    assert "subtracts" in coder.diagnosis
    assert [event.event_type for event in result.events] == [
        "repair_context_received",
        "repair_diagnosed",
        "code_repaired",
        "repair_verified",
    ]
