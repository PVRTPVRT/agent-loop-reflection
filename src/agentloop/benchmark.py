"""Direct and Reflection benchmark strategies with shared hidden evaluation."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Protocol

from agentloop.benchmark_models import (
    AggregateMetrics,
    BenchmarkDataset,
    BenchmarkReport,
    BenchmarkTask,
    StrategyTaskResult,
    UsageMetrics,
)
from agentloop.llm import LLMProvider
from agentloop.models import CodingTask, LLMRequest, LLMResponse
from agentloop.parsing import extract_python_code
from agentloop.verifier import CodeVerifier
from agentloop.workflow import ReflectionWorkflow


class MeteredLLMProvider:
    """Collect request and token metrics without changing the wrapped provider."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.reset()

    def reset(self) -> None:
        self.model_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def generate(self, request: LLMRequest) -> LLMResponse:
        response = self.provider.generate(request)
        self.model_calls += 1
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        self.total_tokens += response.usage.total_tokens
        return response

    def snapshot(self) -> UsageMetrics:
        return UsageMetrics(
            model_calls=self.model_calls,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=self.total_tokens,
        )


class BenchmarkStrategy(Protocol):
    name: str

    def run(self, task: BenchmarkTask) -> StrategyTaskResult:
        """Run one task and score it only against the benchmark evaluation suite."""


class DirectStrategy:
    name = "direct"

    def __init__(
        self,
        *,
        provider: MeteredLLMProvider,
        verifier: CodeVerifier,
    ) -> None:
        self.provider = provider
        self.verifier = verifier

    def run(self, task: BenchmarkTask) -> StrategyTaskResult:
        self.provider.reset()
        started = time.perf_counter()
        response = self.provider.generate(
            LLMRequest(
                system_prompt=(
                    "你是 Python 程序员。只输出完整可运行的 Python 代码，不要解释，不要编写测试。"
                ),
                user_prompt=(
                    f"任务：\n{task.prompt}\n\n必须定义函数：{task.evaluation_suite.function_name}"
                ),
                metadata={
                    "strategy": self.name,
                    "task_id": task.task_id,
                },
            )
        )
        code = extract_python_code(response.text)
        verification = self.verifier.verify(code, task.evaluation_suite)
        return StrategyTaskResult(
            task_id=task.task_id,
            strategy=self.name,
            success=verification.success,
            internal_success=None,
            duration_ms=(time.perf_counter() - started) * 1_000,
            message=verification.message,
            code=code,
            usage=self.provider.snapshot(),
        )


class ReflectionStrategy:
    name = "reflection"

    def __init__(
        self,
        *,
        workflow: ReflectionWorkflow,
        provider: MeteredLLMProvider,
        benchmark_verifier: CodeVerifier,
    ) -> None:
        self.workflow = workflow
        self.provider = provider
        self.benchmark_verifier = benchmark_verifier

    def run(self, task: BenchmarkTask) -> StrategyTaskResult:
        self.provider.reset()
        started = time.perf_counter()
        workflow_result = self.workflow.run(
            CodingTask(
                task_id=task.task_id,
                prompt=task.prompt,
                category=task.category,
                metadata={"difficulty": task.difficulty},
            )
        )
        final_verification = (
            self.benchmark_verifier.verify(
                workflow_result.code,
                task.evaluation_suite,
            )
            if workflow_result.code
            else None
        )
        success = bool(final_verification and final_verification.success)
        message = (
            final_verification.message if final_verification else workflow_result.final_message
        )
        return StrategyTaskResult(
            task_id=task.task_id,
            strategy=self.name,
            success=success,
            internal_success=workflow_result.success,
            duration_ms=(time.perf_counter() - started) * 1_000,
            coding_rounds=workflow_result.coding_rounds,
            debate_rounds=workflow_result.debate_rounds,
            message=message,
            code=workflow_result.code,
            usage=self.provider.snapshot(),
        )


class BenchmarkRunner:
    def run(
        self,
        dataset: BenchmarkDataset,
        strategies: list[BenchmarkStrategy],
        *,
        limit: int | None = None,
    ) -> BenchmarkReport:
        tasks = dataset.tasks[:limit] if limit else dataset.tasks
        results = [strategy.run(task) for strategy in strategies for task in tasks]
        return BenchmarkReport(
            dataset_id=dataset.dataset_id,
            dataset_fingerprint=dataset.fingerprint,
            created_at=datetime.now(UTC).isoformat(),
            results=results,
            aggregates=self._aggregate(results),
        )

    @staticmethod
    def _aggregate(
        results: list[StrategyTaskResult],
    ) -> list[AggregateMetrics]:
        grouped: dict[str, list[StrategyTaskResult]] = defaultdict(list)
        for result in results:
            grouped[result.strategy].append(result)

        aggregates = []
        for strategy, strategy_results in sorted(grouped.items()):
            total = len(strategy_results)
            passed = sum(result.success for result in strategy_results)
            aggregates.append(
                AggregateMetrics(
                    strategy=strategy,
                    total_tasks=total,
                    passed_tasks=passed,
                    pass_rate=passed / total if total else 0,
                    average_duration_ms=sum(result.duration_ms for result in strategy_results)
                    / total,
                    average_model_calls=sum(result.usage.model_calls for result in strategy_results)
                    / total,
                    average_total_tokens=sum(
                        result.usage.total_tokens for result in strategy_results
                    )
                    / total,
                    average_coding_rounds=sum(result.coding_rounds for result in strategy_results)
                    / total,
                )
            )
        return aggregates
