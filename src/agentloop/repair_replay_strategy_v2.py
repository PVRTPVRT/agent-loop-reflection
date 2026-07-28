"""Replay a recorded Direct failure through the evidence-driven repair path."""

from __future__ import annotations

import json
import time
from pathlib import Path

from agentloop.benchmark import MeteredLLMProvider
from agentloop.benchmark_models import StrategyTaskResult
from agentloop.evaluation_v2_models import EvaluationTask
from agentloop.repair_v2 import RepairContext
from agentloop.routing_suites import RoutingSuiteRegistry
from agentloop.telemetry import traced_task_method


class RepairReplayStrategyV2:
    """Validate repair behavior without presenting fault injection as a natural run."""

    name = "repair-replay"

    def __init__(
        self,
        *,
        provider: MeteredLLMProvider,
        verifier,
        repair_workflow,
        routing_suites: RoutingSuiteRegistry,
        recorded_candidate: str,
        candidate_source: str,
        trace_dir: Path,
    ) -> None:
        self.provider = provider
        self.verifier = verifier
        self.repair_workflow = repair_workflow
        self.routing_suites = routing_suites
        self.recorded_candidate = recorded_candidate
        self.candidate_source = candidate_source
        self.trace_dir = trace_dir

    @traced_task_method("agentloop.repair_replay.task")
    def run(self, task: EvaluationTask) -> StrategyTaskResult:
        self.provider.reset()
        started = time.perf_counter()
        routing_suite = self.routing_suites.require(task.task_id)
        recorded_failure = self.verifier.verify(
            self.recorded_candidate,
            routing_suite,
        )
        if recorded_failure.success:
            raise ValueError(
                "Recorded candidate unexpectedly passes the routing suite; "
                "repair replay requires a reproducible failure"
            )

        repair_context = RepairContext(
            task_id=task.task_id,
            failed_code=self.recorded_candidate,
            routing_suite=routing_suite,
            verification_message=recorded_failure.message,
        )
        workflow_result = self.repair_workflow.run(
            task,
            repair_context=repair_context,
        )
        hidden_verification = (
            self.verifier.verify(workflow_result.code, task.evaluation_suite)
            if workflow_result.code
            else None
        )
        success = bool(
            workflow_result.success
            and hidden_verification
            and hidden_verification.success
        )
        if workflow_result.success and hidden_verification:
            message = hidden_verification.message
        else:
            message = workflow_result.final_message

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
            experiment_type="recorded-failure-replay",
            candidate_source=self.candidate_source,
            recorded_candidate=self.recorded_candidate,
            recorded_failure=recorded_failure,
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
