from agentloop.benchmark_models import (
    BenchmarkDataset,
    BenchmarkTask,
    StrategyTaskResult,
)
from agentloop.models import TestCase, TestSuite
from agentloop.resilient_benchmark import ResilientBenchmarkRunner


def make_dataset() -> BenchmarkDataset:
    suite = TestSuite(
        function_name="identity",
        test_cases=[TestCase(args=[1], expected=1, description="one")],
    )
    return BenchmarkDataset(
        schema_version="1.0",
        dataset_id="resilience-test",
        description="Two deterministic tasks.",
        tasks=[
            BenchmarkTask(
                task_id="first",
                category="test",
                difficulty="easy",
                prompt="First",
                evaluation_suite=suite,
            ),
            BenchmarkTask(
                task_id="second",
                category="test",
                difficulty="easy",
                prompt="Second",
                evaluation_suite=suite,
            ),
        ],
    )


class FailsOnceStrategy:
    name = "reflection"

    def run(self, task: BenchmarkTask) -> StrategyTaskResult:
        if task.task_id == "first":
            raise RuntimeError("simulated provider failure")
        return StrategyTaskResult(
            task_id=task.task_id,
            strategy=self.name,
            success=True,
            duration_ms=1,
            message="passed",
        )


def test_runner_continues_and_checkpoints_after_task_failure(tmp_path) -> None:
    checkpoint = tmp_path / "checkpoint.json"

    report = ResilientBenchmarkRunner().run(
        make_dataset(),
        [FailsOnceStrategy()],
        checkpoint_path=checkpoint,
    )

    assert len(report.results) == 2
    assert report.results[0].success is False
    assert "simulated provider failure" in report.results[0].message
    assert report.results[1].success is True
    assert report.aggregates[0].passed_tasks == 1
    assert checkpoint.exists()
    assert "simulated provider failure" in checkpoint.read_text(encoding="utf-8")
