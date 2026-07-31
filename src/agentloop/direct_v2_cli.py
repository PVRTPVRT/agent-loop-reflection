"""Bounded Direct V2 benchmark runner."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentloop.benchmark import MeteredLLMProvider
from agentloop.benchmark_v2 import DirectStrategyV2
from agentloop.bounded_v2_llm import BoundedStrictV2Provider
from agentloop.config import AppSettings, ConfigurationError
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.evaluation_verifier import EvaluationCodeVerifier
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2
from agentloop.resilient_benchmark import ResilientBenchmarkRunner
from agentloop.telemetry import TelemetryConfigurationError, telemetry_session


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run bounded Direct V2.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/datasets/coding-v2-full.json"),
    )
    parser.add_argument("--model", default="gpt-5.4-nano")
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high"],
        default="none",
    )
    parser.add_argument("--request-timeout", type=float, default=60.0)
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/results/direct-v2-nano.json"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = AppSettings.from_env()
        api_key = settings.require_api_key()
        dataset = EvaluationDataset.load(args.dataset)
    except (ConfigurationError, OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    meter = MeteredLLMProvider(
        BoundedStrictV2Provider(
            api_key=api_key,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            request_timeout_seconds=args.request_timeout,
            max_retries=args.max_retries,
        )
    )
    strategy = DirectStrategyV2(
        provider=meter,
        verifier=EvaluationCodeVerifier(sandbox=ManagedDockerSandboxV2()),
    )
    try:
        with telemetry_session():
            report = ResilientBenchmarkRunner().run(
                dataset,
                [strategy],
                checkpoint_path=args.output,
            )
    except TelemetryConfigurationError as exc:
        print(f"Telemetry configuration error: {exc}", file=sys.stderr)
        return 2
    aggregate = report.aggregates[0]
    print(
        f"direct: {aggregate.passed_tasks}/{aggregate.total_tasks}, "
        f"calls/task={aggregate.average_model_calls:.2f}, "
        f"tokens/task={aggregate.average_total_tokens:.0f}, "
        f"duration/task={aggregate.average_duration_ms:.0f}ms"
    )
    print(f"Checkpoint written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
