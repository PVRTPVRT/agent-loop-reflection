from pathlib import Path

from agentloop.agents import CoderAgent, CriticAgent, TesterAgent
from agentloop.benchmark import (
    BenchmarkRunner,
    DirectStrategy,
    MeteredLLMProvider,
    ReflectionStrategy,
)
from agentloop.benchmark_models import BenchmarkDataset
from agentloop.llm import FakeLLMProvider
from agentloop.models import LLMResponse, TestSuite, TokenUsage
from agentloop.verifier import VerificationResult
from agentloop.workflow import ReflectionWorkflow

DATASET_PATH = Path("benchmarks/datasets/coding-v1.json")


class FunctionNameVerifier:
    def verify(self, code: str, suite: TestSuite) -> VerificationResult:
        success = f"def {suite.function_name}" in code and "return a + b" in code
        return VerificationResult(
            success=success,
            message="通过验证" if success else "隐藏测试失败",
        )


def test_versioned_dataset_loads_and_has_stable_fingerprint() -> None:
    first = BenchmarkDataset.load(DATASET_PATH)
    second = BenchmarkDataset.load(DATASET_PATH)

    assert first.dataset_id == "coding-v1"
    assert len(first.tasks) == 8
    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 16


def test_direct_strategy_records_usage_and_hidden_result() -> None:
    provider = MeteredLLMProvider(
        FakeLLMProvider(
            [
                LLMResponse(
                    text="def add(a, b):\n    return a + b",
                    model="fake",
                    usage=TokenUsage(
                        input_tokens=10,
                        output_tokens=5,
                        total_tokens=15,
                    ),
                )
            ]
        )
    )
    task = BenchmarkDataset.load(DATASET_PATH).tasks[0]

    result = DirectStrategy(
        provider=provider,
        verifier=FunctionNameVerifier(),
    ).run(task)

    assert result.success
    assert result.internal_success is None
    assert result.usage.model_calls == 1
    assert result.usage.total_tokens == 15


def test_reflection_is_scored_against_independent_suite() -> None:
    fake = FakeLLMProvider(
        [
            """{"function_name":"add","test_cases":[
              {"args":[1,2],"expected":-1,"description":"incorrect internal"}
            ]}""",
            "[APPROVED]",
            "def add(a, b):\n    return a - b",
        ]
    )
    meter = MeteredLLMProvider(fake)

    class AlwaysPassInternalVerifier:
        def verify(self, code: str, suite: TestSuite) -> VerificationResult:
            return VerificationResult(success=True, message="内部测试通过")

    workflow = ReflectionWorkflow(
        tester=TesterAgent(meter),
        critic=CriticAgent(meter),
        coder=CoderAgent(meter),
        verifier=AlwaysPassInternalVerifier(),
    )
    task = BenchmarkDataset.load(DATASET_PATH).tasks[0]

    result = ReflectionStrategy(
        workflow=workflow,
        provider=meter,
        benchmark_verifier=FunctionNameVerifier(),
    ).run(task)

    assert result.internal_success is True
    assert result.success is False
    assert result.message == "隐藏测试失败"
    assert result.usage.model_calls == 3


def test_runner_aggregates_strategies() -> None:
    dataset = BenchmarkDataset.load(DATASET_PATH)

    class FixedStrategy:
        def __init__(self, name: str, success: bool) -> None:
            self.name = name
            self.success = success

        def run(self, task):
            from agentloop.benchmark_models import StrategyTaskResult

            return StrategyTaskResult(
                task_id=task.task_id,
                strategy=self.name,
                success=self.success,
                duration_ms=10,
                message="done",
            )

    report = BenchmarkRunner().run(
        dataset,
        [FixedStrategy("direct", False), FixedStrategy("reflection", True)],
        limit=2,
    )

    aggregates = {item.strategy: item for item in report.aggregates}
    assert len(report.results) == 4
    assert aggregates["direct"].pass_rate == 0
    assert aggregates["reflection"].pass_rate == 1
