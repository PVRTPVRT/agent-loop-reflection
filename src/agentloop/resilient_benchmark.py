"""Benchmark runner that isolates failures and writes incremental checkpoints."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

from agentloop.benchmark import BenchmarkRunner, BenchmarkStrategy
from agentloop.benchmark_models import (
    BenchmarkDataset,
    BenchmarkReport,
    StrategyTaskResult,
    UsageMetrics,
)


class ResilientBenchmarkRunner:
    """Continue after a task failure so paid runs retain useful partial results."""

    def run(
        self,
        dataset: BenchmarkDataset,
        strategies: list[BenchmarkStrategy],
        *,
        limit: int | None = None,
        checkpoint_path: Path | None = None,
    ) -> BenchmarkReport:
        tasks = dataset.tasks[:limit] if limit else dataset.tasks
        results: list[StrategyTaskResult] = []

        for strategy in strategies:
            for task in tasks:
                started = time.perf_counter()
                try:
                    result = strategy.run(task)
                except Exception as exc:  # noqa: BLE001
                    provider = getattr(strategy, "provider", None)
                    usage = (
                        provider.snapshot()
                        if provider is not None and hasattr(provider, "snapshot")
                        else UsageMetrics()
                    )
                    result = StrategyTaskResult(
                        task_id=task.task_id,
                        strategy=strategy.name,
                        success=False,
                        internal_success=False,
                        duration_ms=(time.perf_counter() - started) * 1_000,
                        coding_rounds=0,
                        message=f"{type(exc).__name__}: {exc}",
                        usage=usage,
                    )
                results.append(result)
                report = self._build_report(dataset, results)
                if checkpoint_path:
                    self._write_checkpoint(report, checkpoint_path)

        return self._build_report(dataset, results)

    @staticmethod
    def _build_report(
        dataset: BenchmarkDataset,
        results: list[StrategyTaskResult],
    ) -> BenchmarkReport:
        return BenchmarkReport(
            dataset_id=dataset.dataset_id,
            dataset_fingerprint=dataset.fingerprint,
            created_at=datetime.now(UTC).isoformat(),
            results=results,
            aggregates=BenchmarkRunner._aggregate(results),
        )

    @staticmethod
    def _write_checkpoint(report: BenchmarkReport, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
