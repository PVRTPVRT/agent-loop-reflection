"""Public routing suites kept separate from hidden benchmark evaluation."""

from __future__ import annotations

from pathlib import Path

from agentloop.evaluation_v2_models import EvaluationDataset, EvaluationSuite

DEFAULT_ROUTING_PATH = Path("benchmarks/routing/coding-v2-routing.json")


class RoutingSuiteRegistry:
    def __init__(self, suites: dict[str, EvaluationSuite]) -> None:
        self.suites = suites

    @classmethod
    def load(
        cls,
        path: str | Path = DEFAULT_ROUTING_PATH,
    ) -> RoutingSuiteRegistry:
        dataset = EvaluationDataset.load(path)
        return cls({task.task_id: task.evaluation_suite for task in dataset.tasks})

    def require(self, task_id: str) -> EvaluationSuite:
        try:
            return self.suites[task_id]
        except KeyError as exc:
            raise ValueError(f"No public routing suite for task {task_id!r}") from exc
