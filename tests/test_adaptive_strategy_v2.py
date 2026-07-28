import json

from agentloop.adaptive_strategy_v2 import AdaptiveStrategyV2
from agentloop.benchmark import MeteredLLMProvider
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.evaluation_workflow import EvaluationWorkflowResult
from agentloop.llm import FakeLLMProvider
from agentloop.models import AgentEvent
from agentloop.routing_suites import RoutingSuiteRegistry
from agentloop.verifier import VerificationResult


class CodeVerifier:
    def verify(self, code, suite):
        success = "return a + b" in code
        return VerificationResult(
            success=success,
            message="passed" if success else "failed route",
        )


class ForbiddenWorkflow:
    def run(self, task):
        raise AssertionError("Reflection must not run after route success")


class FixedWorkflow:
    def __init__(self, task):
        self.task = task
        self.calls = 0
        self.repair_context = None

    def run(self, task, *, repair_context):
        self.calls += 1
        self.repair_context = repair_context
        return EvaluationWorkflowResult(
            task_id=task.task_id,
            success=True,
            code="def add(a, b):\n    return a + b",
            test_suite=self.task.evaluation_suite,
            debate_rounds=1,
            coding_rounds=1,
            final_message="repaired",
            events=(
                AgentEvent(
                    agent="workflow",
                    event_type="fallback",
                ),
            ),
        )


def task():
    return EvaluationDataset.load("benchmarks/datasets/coding-v2-full.json").tasks[0]


def test_route_success_returns_direct_without_reflection(tmp_path) -> None:
    meter = MeteredLLMProvider(FakeLLMProvider(["def add(a, b):\n    return a + b"]))
    strategy = AdaptiveStrategyV2(
        provider=meter,
        verifier=CodeVerifier(),
        reflection_workflow=ForbiddenWorkflow(),
        routing_suites=RoutingSuiteRegistry.load(),
        trace_dir=tmp_path,
    )

    result = strategy.run(task())

    assert result.success is True
    assert result.usage.model_calls == 1
    trace = json.loads((tmp_path / "add-001.json").read_text(encoding="utf-8"))
    assert trace["path"] == "direct"


def test_route_failure_falls_back_to_reflection(tmp_path) -> None:
    benchmark_task = task()
    meter = MeteredLLMProvider(FakeLLMProvider(["def add(a, b):\n    return a - b"]))
    workflow = FixedWorkflow(benchmark_task)
    strategy = AdaptiveStrategyV2(
        provider=meter,
        verifier=CodeVerifier(),
        reflection_workflow=workflow,
        routing_suites=RoutingSuiteRegistry.load(),
        trace_dir=tmp_path,
    )

    result = strategy.run(benchmark_task)

    assert result.success is True
    assert workflow.calls == 1
    assert workflow.repair_context.failed_code == "def add(a, b):\n    return a - b"
    assert workflow.repair_context.verification_message == "failed route"
    assert workflow.repair_context.routing_suite.function_name == "add"
    assert result.coding_rounds == 2
    trace = json.loads((tmp_path / "add-001.json").read_text(encoding="utf-8"))
    assert trace["path"] == "reflection"
    assert trace["repair_context"]["verification_message"] == "failed route"
