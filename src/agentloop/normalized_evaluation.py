"""V2 Tester and workflow with deterministic semantic normalization."""

from __future__ import annotations

import json

from pydantic import ValidationError

from agentloop.contracts_v2 import render_contract
from agentloop.evaluation_agents import (
    V2_TESTER_SYSTEM,
    EvaluationTesterAgent,
)
from agentloop.evaluation_v2_models import EvaluationSuite
from agentloop.evaluation_workflow import EvaluationReflectionWorkflow
from agentloop.models import AgentEvent, LLMRequest
from agentloop.parsing import ModelOutputError, extract_json_object
from agentloop.suite_normalization import normalize_suite
from agentloop.suite_validation import SuiteContractError


class NormalizedEvaluationTesterAgent(EvaluationTesterAgent):
    def __init__(self, provider, **kwargs) -> None:
        super().__init__(provider, **kwargs)
        self.normalization_history: list[tuple[str, ...]] = []

    def create_suite(self, task, *, critique: str = "") -> EvaluationSuite:
        contract = self.registry.require(task.task_id)
        feedback = critique
        for _ in range(self.retries + 1):
            response = self.provider.generate(
                LLMRequest(
                    system_prompt=V2_TESTER_SYSTEM,
                    user_prompt=(
                        f"原始任务：\n{task.prompt}\n\n公开契约：\n"
                        f"{render_contract(contract)}"
                        + (f"\n\n修订反馈：\n{feedback}" if feedback else "")
                    ),
                    metadata={"agent": "tester", "task_id": task.task_id},
                )
            )
            try:
                raw_suite = EvaluationSuite.model_validate(extract_json_object(response.text))
                normalized = normalize_suite(raw_suite, contract)
                self.normalization_history.append(normalized.corrections)
                return normalized.suite
            except (
                ModelOutputError,
                ValidationError,
                SuiteContractError,
            ) as exc:
                feedback = f"结构或输入域校验失败：{exc}\n请修正结构或生成至少一个契约内用例。"
        raise ModelOutputError(
            f"Tester failed V2 normalization after {self.retries + 1} attempts: {feedback}"
        )


class NormalizedEvaluationWorkflow(EvaluationReflectionWorkflow):
    def run(self, task):
        history_start = len(self.tester.normalization_history)
        result = super().run(task)
        new_history = self.tester.normalization_history[history_start:]
        corrections = [correction for batch in new_history for correction in batch]
        event = AgentEvent(
            agent="tester",
            event_type="suite_normalized",
            message=json.dumps(corrections, ensure_ascii=False),
            metadata={
                "correction_count": len(corrections),
                "suite_versions": len(new_history),
            },
        )
        return result.model_copy(update={"events": (*result.events, event)})
