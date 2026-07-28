import json
from pathlib import Path

from agentloop.agents import CoderAgent, CriticAgent, TesterAgent
from agentloop.benchmark import MeteredLLMProvider
from agentloop.benchmark_models import BenchmarkDataset
from agentloop.llm import FakeLLMProvider
from agentloop.models import TestSuite
from agentloop.observable_benchmark import ObservableReflectionStrategy
from agentloop.verifier import VerificationResult
from agentloop.workflow import ReflectionWorkflow


class AlwaysPassVerifier:
    def verify(self, code: str, suite: TestSuite) -> VerificationResult:
        return VerificationResult(success=True, message="passed")


def test_observable_strategy_persists_suite_events_and_verdict(tmp_path) -> None:
    meter = MeteredLLMProvider(
        FakeLLMProvider(
            [
                """{"function_name":"add","test_cases":[
                {"args":[1,2],"expected":3,"description":"normal"}]}""",
                "[APPROVED]",
                "def add(a, b):\n    return a + b",
            ]
        )
    )
    verifier = AlwaysPassVerifier()
    workflow = ReflectionWorkflow(
        tester=TesterAgent(meter),
        critic=CriticAgent(meter),
        coder=CoderAgent(meter),
        verifier=verifier,
    )
    strategy = ObservableReflectionStrategy(
        workflow=workflow,
        provider=meter,
        benchmark_verifier=verifier,
        trace_dir=tmp_path,
    )

    strategy.run(BenchmarkDataset.load(Path("benchmarks/datasets/coding-v1.json")).tasks[0])

    trace = json.loads((tmp_path / "add-001.json").read_text(encoding="utf-8"))
    assert trace["internal_workflow"]["test_suite"]["function_name"] == "add"
    assert trace["internal_workflow"]["events"][1]["event_type"] == "suite_reviewed"
    assert trace["benchmark_verification"]["success"] is True
