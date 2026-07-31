"""Direct and observable Reflection strategies for V2 evaluation tasks."""

from __future__ import annotations

import json
import time
from pathlib import Path

from agentloop.benchmark import MeteredLLMProvider
from agentloop.benchmark_models import StrategyTaskResult
from agentloop.evaluation_v2_models import EvaluationTask
from agentloop.models import LLMRequest
from agentloop.parsing import extract_python_code
from agentloop.telemetry import traced_task_method


class DirectStrategyV2:
    name = "direct"

    def __init__(self, *, provider: MeteredLLMProvider, verifier) -> None:
        self.provider = provider
        self.verifier = verifier

    @traced_task_method("agentloop.strategy.task")
    def run(self, task: EvaluationTask) -> StrategyTaskResult:
        self.provider.reset()
        started = time.perf_counter()
        response = self.provider.generate(
            LLMRequest(
                system_prompt=(
                    "你是 Python 程序员。实现给定任务，包括题目明确要求的异常。"
                    "只输出完整可运行代码，不要解释或编写测试。"
                ),
                user_prompt=task.prompt,
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


class ObservableReflectionStrategyV2:
    name = "reflection"

    def __init__(
        self,
        *,
        workflow,
        provider: MeteredLLMProvider,
        benchmark_verifier,
        trace_dir: Path,
    ) -> None:
        self.workflow = workflow
        self.provider = provider
        self.benchmark_verifier = benchmark_verifier
        self.trace_dir = trace_dir

    @traced_task_method("agentloop.strategy.task")
    def run(self, task: EvaluationTask) -> StrategyTaskResult:
        self.provider.reset()
        started = time.perf_counter()
        workflow_result = self.workflow.run(task)
        external = (
            self.benchmark_verifier.verify(workflow_result.code, task.evaluation_suite)
            if workflow_result.code
            else None
        )
        result = StrategyTaskResult(
            task_id=task.task_id,
            strategy=self.name,
            success=bool(external and external.success),
            internal_success=workflow_result.success,
            duration_ms=(time.perf_counter() - started) * 1_000,
            coding_rounds=workflow_result.coding_rounds,
            debate_rounds=workflow_result.debate_rounds,
            message=external.message if external else workflow_result.final_message,
            code=workflow_result.code,
            usage=self.provider.snapshot(),
        )
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        trace = {
            "task": task.model_dump(mode="json"),
            "internal_workflow": workflow_result.model_dump(mode="json"),
            "benchmark_verification": (external.model_dump(mode="json") if external else None),
            "result": result.model_dump(mode="json"),
        }
        (self.trace_dir / f"{task.task_id}.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result
