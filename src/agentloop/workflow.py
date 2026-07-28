"""Explicit reflection workflow coordinating the agent roles."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from agentloop.agents import CoderAgent, CriticAgent, TesterAgent
from agentloop.models import AgentEvent, CodingTask, TestSuite
from agentloop.verifier import CodeVerifier


class WorkflowResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    success: bool
    code: str | None = None
    test_suite: TestSuite
    debate_rounds: int = Field(ge=1)
    coding_rounds: int = Field(ge=0)
    final_message: str
    events: tuple[AgentEvent, ...]


class ReflectionWorkflow:
    def __init__(
        self,
        *,
        tester: TesterAgent,
        critic: CriticAgent,
        coder: CoderAgent,
        verifier: CodeVerifier,
        max_debate_rounds: int = 2,
        max_coding_rounds: int = 3,
    ) -> None:
        if max_debate_rounds < 1 or max_coding_rounds < 1:
            raise ValueError("workflow round limits must be positive")
        self.tester = tester
        self.critic = critic
        self.coder = coder
        self.verifier = verifier
        self.max_debate_rounds = max_debate_rounds
        self.max_coding_rounds = max_coding_rounds

    def run(self, task: CodingTask) -> WorkflowResult:
        events: list[AgentEvent] = []
        suite = self.tester.create_suite(task)
        events.append(
            AgentEvent(
                agent="tester",
                event_type="suite_created",
                metadata={"case_count": len(suite.test_cases)},
            )
        )

        debate_rounds = 0
        for debate_rounds in range(1, self.max_debate_rounds + 1):
            verdict = self.critic.review(task, suite)
            approved = self.critic.is_approved(verdict)
            events.append(
                AgentEvent(
                    agent="critic",
                    event_type="suite_reviewed",
                    message=verdict,
                    metadata={"approved": approved, "round": debate_rounds},
                )
            )
            if approved:
                break
            if debate_rounds < self.max_debate_rounds:
                suite = self.tester.create_suite(task, critique=verdict)
                events.append(
                    AgentEvent(
                        agent="tester",
                        event_type="suite_revised",
                        metadata={"round": debate_rounds},
                    )
                )

        feedback = ""
        last_code: str | None = None
        for coding_round in range(1, self.max_coding_rounds + 1):
            last_code = self.coder.generate_code(
                task,
                suite,
                feedback=feedback,
            )
            events.append(
                AgentEvent(
                    agent="coder",
                    event_type="code_generated",
                    metadata={"round": coding_round, "is_revision": bool(feedback)},
                )
            )
            verification = self.verifier.verify(last_code, suite)
            events.append(
                AgentEvent(
                    agent="verifier",
                    event_type="code_verified",
                    message=verification.message,
                    metadata={
                        "round": coding_round,
                        "success": verification.success,
                    },
                )
            )
            if verification.success:
                return WorkflowResult(
                    task_id=task.task_id,
                    success=True,
                    code=last_code,
                    test_suite=suite,
                    debate_rounds=debate_rounds,
                    coding_rounds=coding_round,
                    final_message=verification.message,
                    events=tuple(events),
                )
            feedback = verification.message

        return WorkflowResult(
            task_id=task.task_id,
            success=False,
            code=last_code,
            test_suite=suite,
            debate_rounds=debate_rounds,
            coding_rounds=self.max_coding_rounds,
            final_message=feedback,
            events=tuple(events),
        )
