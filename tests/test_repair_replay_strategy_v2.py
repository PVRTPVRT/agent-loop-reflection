import json

import pytest

from agentloop.benchmark import MeteredLLMProvider
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.evaluation_workflow import EvaluationWorkflowResult
from agentloop.llm import FakeLLMProvider
from agentloop.repair_replay_strategy_v2 import RepairReplayStrategyV2
from agentloop.routing_suites import RoutingSuiteRegistry
from agentloop.verifier import VerificationResult


class AddVerifier:
    def verify(self, code, suite):
        success = "return a + b" in code
        return VerificationResult(
            success=success,
            message="passed" if success else "recorded route failure",
        )


class SuccessfulRepair:
    def run(self, task, *, repair_context):
        return EvaluationWorkflowResult(
            task_id=task.task_id,
            success=True,
            code="def add(a, b):\n    return a + b",
            test_suite=repair_context.routing_suite,
            debate_rounds=1,
            coding_rounds=1,
            final_message="route repaired",
            events=(),
        )


def add_task():
    return EvaluationDataset.load("benchmarks/datasets/coding-v2-full.json").tasks[0]


def build_strategy(tmp_path, candidate: str) -> RepairReplayStrategyV2:
    return RepairReplayStrategyV2(
        provider=MeteredLLMProvider(FakeLLMProvider([])),
        verifier=AddVerifier(),
        repair_workflow=SuccessfulRepair(),
        routing_suites=RoutingSuiteRegistry.load(),
        recorded_candidate=candidate,
        candidate_source="tests/fixture.py",
        trace_dir=tmp_path,
    )


def test_replay_requires_and_repairs_recorded_failure(tmp_path) -> None:
    result = build_strategy(
        tmp_path,
        "def add(a, b):\n    return a - b",
    ).run(add_task())

    assert result.success is True
    assert result.internal_success is True
    trace = json.loads((tmp_path / "add-001.json").read_text(encoding="utf-8"))
    assert trace["experiment_type"] == "recorded-failure-replay"
    assert trace["recorded_failure"]["success"] is False
    assert trace["hidden_verification"]["success"] is True


def test_replay_rejects_candidate_that_no_longer_fails(tmp_path) -> None:
    strategy = build_strategy(
        tmp_path,
        "def add(a, b):\n    return a + b",
    )

    with pytest.raises(ValueError, match="unexpectedly passes"):
        strategy.run(add_task())
