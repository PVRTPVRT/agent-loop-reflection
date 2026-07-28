import json

from agentloop.adaptive_strategy_v2 import AdaptiveStrategyV2
from agentloop.benchmark import MeteredLLMProvider
from agentloop.evaluation_v2_models import (
    EvaluationCase,
    EvaluationDataset,
    EvaluationSuite,
)
from agentloop.evaluation_workflow import EvaluationWorkflowResult
from agentloop.llm import FakeLLMProvider
from agentloop.repair_v2 import RepairContext
from agentloop.repair_workflow_v2 import EvidenceDrivenRepairWorkflow
from agentloop.routing_suites import RoutingSuiteRegistry
from agentloop.verifier import VerificationResult


class ForbiddenTester:
    def __init__(self) -> None:
        self.normalization_history = []

    def create_suite(self, task, *, critique=""):
        raise AssertionError("Repair mode must reuse routing evidence")


class RecordingCritic:
    def __init__(self) -> None:
        self.contexts = []

    def diagnose_repair(self, task, context):
        self.contexts.append(context)
        return f"diagnosis-{len(self.contexts)}"


class TwoAttemptCoder:
    def __init__(self) -> None:
        self.contexts = []

    def repair_code(self, task, context, *, diagnosis, feedback=""):
        self.contexts.append(context)
        if len(self.contexts) == 1:
            return "def add(a, b):\n    return a * b"
        return "def add(a, b):\n    return a + b"


class AddVerifier:
    def verify(self, code, suite):
        success = "return a + b" in code
        return VerificationResult(
            success=success,
            message="passed repair route" if success else "route still failing",
        )


class FailedRepairWorkflow:
    def __init__(self, benchmark_task) -> None:
        self.task = benchmark_task

    def run(self, task, *, repair_context):
        return EvaluationWorkflowResult(
            task_id=task.task_id,
            success=False,
            code="def add(a, b):\n    return a + b",
            test_suite=repair_context.routing_suite,
            debate_rounds=2,
            coding_rounds=2,
            final_message="internal route still failing",
            events=(),
        )


def add_task():
    return EvaluationDataset.load("benchmarks/datasets/coding-v2-full.json").tasks[0]


def add_suite() -> EvaluationSuite:
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


def test_repair_round_uses_latest_candidate_and_failure() -> None:
    task = add_task()
    context = RepairContext(
        task_id=task.task_id,
        failed_code="def add(a, b):\n    return a - b",
        routing_suite=add_suite(),
        verification_message="initial route failure",
    )
    critic = RecordingCritic()
    coder = TwoAttemptCoder()
    workflow = EvidenceDrivenRepairWorkflow(
        tester=ForbiddenTester(),
        critic=critic,
        coder=coder,
        verifier=AddVerifier(),
        max_coding_rounds=2,
    )

    result = workflow.run(task, repair_context=context)

    assert result.success is True
    assert result.coding_rounds == 2
    assert result.debate_rounds == 2
    assert critic.contexts[0] is context
    assert critic.contexts[1].failed_code == "def add(a, b):\n    return a * b"
    assert critic.contexts[1].verification_message == "route still failing"
    assert coder.contexts[1] is critic.contexts[1]
    assert [event.event_type for event in result.events] == [
        "repair_context_received",
        "repair_diagnosed",
        "code_repaired",
        "repair_verified",
        "repair_diagnosed",
        "code_repaired",
        "repair_verified",
    ]


def test_internal_repair_failure_cannot_be_hidden_by_final_suite(tmp_path) -> None:
    task = add_task()
    provider = MeteredLLMProvider(
        FakeLLMProvider(["def add(a, b):\n    return a - b"])
    )
    strategy = AdaptiveStrategyV2(
        provider=provider,
        verifier=AddVerifier(),
        reflection_workflow=FailedRepairWorkflow(task),
        routing_suites=RoutingSuiteRegistry.load(),
        trace_dir=tmp_path,
    )

    result = strategy.run(task)

    assert result.internal_success is False
    assert result.success is False
    trace = json.loads((tmp_path / "add-001.json").read_text(encoding="utf-8"))
    assert trace["hidden_verification"]["success"] is True
    assert trace["result"]["success"] is False
