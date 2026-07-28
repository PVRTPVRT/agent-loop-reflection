"""Lean Reflection: machine validation gates, one advisory Critic pass."""

from __future__ import annotations

from agentloop.normalized_evaluation import NormalizedEvaluationWorkflow


class LeanNormalizedEvaluationWorkflow(NormalizedEvaluationWorkflow):
    def __init__(self, *args, **kwargs) -> None:
        kwargs["max_debate_rounds"] = 1
        super().__init__(*args, **kwargs)
