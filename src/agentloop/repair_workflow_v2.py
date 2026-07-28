"""Evidence-driven repair workflow entered only after a failed Direct route."""

from __future__ import annotations

from agentloop.evaluation_v2_models import EvaluationTask
from agentloop.evaluation_workflow import EvaluationWorkflowResult
from agentloop.lean_evaluation import LeanNormalizedEvaluationWorkflow
from agentloop.models import AgentEvent
from agentloop.repair_v2 import RepairContext


class EvidenceDrivenRepairWorkflow(LeanNormalizedEvaluationWorkflow):
    """Diagnose and repair the failed Direct candidate instead of restarting."""

    def run(
        self,
        task: EvaluationTask,
        *,
        repair_context: RepairContext | None = None,
    ) -> EvaluationWorkflowResult:
        if repair_context is None:
            return super().run(task)
        if repair_context.task_id != task.task_id:
            raise ValueError(
                f"Repair context task {repair_context.task_id!r} does not match "
                f"{task.task_id!r}"
            )

        events = [
            AgentEvent(
                agent="workflow",
                event_type="repair_context_received",
                message=repair_context.verification_message,
                metadata={"failed_code": repair_context.failed_code},
            )
        ]
        feedback = repair_context.verification_message
        last_code = repair_context.failed_code
        for coding_round in range(1, self.max_coding_rounds + 1):
            round_context = (
                repair_context
                if coding_round == 1
                else repair_context.model_copy(
                    update={
                        "failed_code": last_code,
                        "verification_message": feedback,
                    }
                )
            )
            diagnosis = self.critic.diagnose_repair(task, round_context)
            events.append(
                AgentEvent(
                    agent="critic",
                    event_type="repair_diagnosed",
                    message=diagnosis,
                    metadata={"round": coding_round},
                )
            )
            previous_code = last_code
            last_code = self.coder.repair_code(
                task,
                round_context,
                diagnosis=diagnosis,
                feedback="" if coding_round == 1 else feedback,
            )
            events.append(
                AgentEvent(
                    agent="coder",
                    event_type="code_repaired",
                    metadata={
                        "round": coding_round,
                        "changed": last_code != previous_code,
                    },
                )
            )
            verification = self.verifier.verify(
                last_code,
                repair_context.routing_suite,
            )
            events.append(
                AgentEvent(
                    agent="verifier",
                    event_type="repair_verified",
                    message=verification.message,
                    metadata={
                        "round": coding_round,
                        "success": verification.success,
                    },
                )
            )
            if verification.success:
                return EvaluationWorkflowResult(
                    task_id=task.task_id,
                    success=True,
                    code=last_code,
                    test_suite=repair_context.routing_suite,
                    debate_rounds=coding_round,
                    coding_rounds=coding_round,
                    final_message=verification.message,
                    events=tuple(events),
                )
            feedback = verification.message

        return EvaluationWorkflowResult(
            task_id=task.task_id,
            success=False,
            code=last_code,
            test_suite=repair_context.routing_suite,
            debate_rounds=self.max_coding_rounds,
            coding_rounds=self.max_coding_rounds,
            final_message=feedback,
            events=tuple(events),
        )
