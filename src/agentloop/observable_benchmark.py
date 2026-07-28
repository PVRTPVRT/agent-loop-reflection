"""Reflection strategy that persists the complete internal decision trace."""

from __future__ import annotations

import json
import time
from pathlib import Path

from agentloop.benchmark import MeteredLLMProvider
from agentloop.benchmark_models import BenchmarkTask, StrategyTaskResult
from agentloop.models import CodingTask
from agentloop.verifier import CodeVerifier
from agentloop.workflow import ReflectionWorkflow


class ObservableReflectionStrategy:
    name = "reflection"

    def __init__(
        self,
        *,
        workflow: ReflectionWorkflow,
        provider: MeteredLLMProvider,
        benchmark_verifier: CodeVerifier,
        trace_dir: Path,
    ) -> None:
        self.workflow = workflow
        self.provider = provider
        self.benchmark_verifier = benchmark_verifier
        self.trace_dir = trace_dir

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
        result = StrategyTaskResult(
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
        self._write_trace(
            task=task,
            workflow_result=workflow_result,
            benchmark_verification=final_verification,
            result=result,
        )
        return result

    def _write_trace(
        self,
        *,
        task: BenchmarkTask,
        workflow_result,
        benchmark_verification,
        result: StrategyTaskResult,
    ) -> None:
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "task": task.model_dump(mode="json"),
            "internal_workflow": workflow_result.model_dump(mode="json"),
            "benchmark_verification": (
                benchmark_verification.model_dump(mode="json") if benchmark_verification else None
            ),
            "result": result.model_dump(mode="json"),
        }
        trace_path = self.trace_dir / f"{task.task_id}.json"
        trace_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
