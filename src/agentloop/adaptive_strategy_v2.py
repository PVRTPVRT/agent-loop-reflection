"""Adaptive strategy: Direct first, Lean Reflection only after route failure."""

from __future__ import annotations

import json
import time
from pathlib import Path

from agentloop.benchmark import MeteredLLMProvider
from agentloop.benchmark_models import StrategyTaskResult
from agentloop.evaluation_v2_models import EvaluationTask
from agentloop.models import LLMRequest
from agentloop.parsing import extract_python_code
from agentloop.repair_v2 import RepairContext
from agentloop.routing_suites import RoutingSuiteRegistry
from agentloop.telemetry import traced_task_method


class AdaptiveStrategyV2:
    name = "adaptive"

    def __init__(
        self,
        *,
        provider: MeteredLLMProvider,
        verifier,
        reflection_workflow,
        routing_suites: RoutingSuiteRegistry,
        trace_dir: Path,
    ) -> None:
        self.provider = provider
        self.verifier = verifier
        self.reflection_workflow = reflection_workflow
        self.routing_suites = routing_suites
        self.trace_dir = trace_dir

    @traced_task_method("agentloop.adaptive.task")
    def run(self, task: EvaluationTask) -> StrategyTaskResult:
        self.provider.reset()
        started = time.perf_counter()
        routing_suite = self.routing_suites.require(task.task_id)
        direct_response = self.provider.generate(
            LLMRequest(
                system_prompt=(
                    "你是 Python 程序员。实现给定任务，包括题目明确要求的异常。"
                    "只输出完整可运行代码，不要解释或编写测试。"
                ),
                user_prompt=task.prompt,
                metadata={
                    "strategy": self.name,
                    "agent": "direct",
                    "task_id": task.task_id,
                },
            )
        )
        direct_code = extract_python_code(direct_response.text)
        routing_verification = self.verifier.verify(direct_code, routing_suite)

        workflow_result = None
        repair_context = None
        if routing_verification.success:
            path = "direct"
            final_code = direct_code
            internal_success = True
            coding_rounds = 1
            debate_rounds = 0
        else:
            path = "reflection"
            repair_context = RepairContext(
                task_id=task.task_id,
                failed_code=direct_code,
                routing_suite=routing_suite,
                verification_message=routing_verification.message,
            )
            workflow_result = self.reflection_workflow.run(
                task,
                repair_context=repair_context,
            )
            final_code = workflow_result.code
            internal_success = workflow_result.success
            coding_rounds = 1 + workflow_result.coding_rounds
            debate_rounds = workflow_result.debate_rounds

        hidden_verification = (
            self.verifier.verify(final_code, task.evaluation_suite) if final_code else None
        )
        final_success = bool(
            internal_success
            and hidden_verification
            and hidden_verification.success
        )
        result = StrategyTaskResult(
            task_id=task.task_id,
            strategy=self.name,
            success=final_success,
            internal_success=internal_success,
            duration_ms=(time.perf_counter() - started) * 1_000,
            coding_rounds=coding_rounds,
            debate_rounds=debate_rounds,
            message=(hidden_verification.message if hidden_verification else "No final code"),
            code=final_code,
            usage=self.provider.snapshot(),
        )
        self._write_trace(
            task=task,
            path=path,
            direct_code=direct_code,
            routing_suite=routing_suite,
            routing_verification=routing_verification,
            repair_context=repair_context,
            workflow_result=workflow_result,
            hidden_verification=hidden_verification,
            result=result,
        )
        return result

    def _write_trace(self, **payload) -> None:
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        task = payload["task"]
        serializable = {}
        for key, value in payload.items():
            if hasattr(value, "model_dump"):
                serializable[key] = value.model_dump(mode="json")
            else:
                serializable[key] = value
        (self.trace_dir / f"{task.task_id}.json").write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
