"""Bounded V2 Reflection runner for targeted and batch regression."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentloop.benchmark import MeteredLLMProvider
from agentloop.benchmark_v2 import ObservableReflectionStrategyV2
from agentloop.bounded_v2_llm import BoundedStrictV2Provider
from agentloop.config import AppSettings, ConfigurationError
from agentloop.evaluation_agents import (
    EvaluationCoderAgent,
    EvaluationCriticAgent,
    EvaluationTesterAgent,
)
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.evaluation_verifier import EvaluationCodeVerifier
from agentloop.evaluation_workflow import EvaluationReflectionWorkflow
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2
from agentloop.resilient_benchmark import ResilientBenchmarkRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run bounded V2 Reflection with validated generated tests."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/datasets/coding-v2-pilot.json"),
    )
    parser.add_argument("--task-id", action="append")
    parser.add_argument("--model", default="gpt-5.4-nano")
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high"],
        default="none",
    )
    parser.add_argument("--request-timeout", type=float, default=30.0)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/results/reflection-v2-bounded-nano.json"),
    )
    parser.add_argument(
        "--trace-dir",
        type=Path,
        default=Path("benchmarks/traces/reflection-v2-bounded-nano"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.request_timeout <= 0 or args.max_retries < 0:
        print("Invalid timeout or retry budget.", file=sys.stderr)
        return 2
    try:
        settings = AppSettings.from_env()
        api_key = settings.require_api_key()
        dataset = EvaluationDataset.load(args.dataset)
    except (ConfigurationError, OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.task_id:
        requested = set(args.task_id)
        selected = [task for task in dataset.tasks if task.task_id in requested]
        missing = requested - {task.task_id for task in selected}
        if missing:
            print(f"Unknown task IDs: {sorted(missing)}", file=sys.stderr)
            return 2
        dataset = dataset.model_copy(update={"tasks": selected})

    meter = MeteredLLMProvider(
        BoundedStrictV2Provider(
            api_key=api_key,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            request_timeout_seconds=args.request_timeout,
            max_retries=args.max_retries,
        )
    )
    verifier = EvaluationCodeVerifier(sandbox=ManagedDockerSandboxV2())
    workflow = EvaluationReflectionWorkflow(
        tester=EvaluationTesterAgent(meter),
        critic=EvaluationCriticAgent(meter),
        coder=EvaluationCoderAgent(meter),
        verifier=verifier,
        max_debate_rounds=settings.max_debate_rounds,
        max_coding_rounds=settings.max_coding_rounds,
    )
    reflection = ObservableReflectionStrategyV2(
        workflow=workflow,
        provider=meter,
        benchmark_verifier=verifier,
        trace_dir=args.trace_dir,
    )
    report = ResilientBenchmarkRunner().run(
        dataset,
        [reflection],
        checkpoint_path=args.output,
    )
    aggregate = report.aggregates[0]
    print(
        f"reflection: {aggregate.passed_tasks}/{aggregate.total_tasks}, "
        f"calls/task={aggregate.average_model_calls:.2f}, "
        f"tokens/task={aggregate.average_total_tokens:.0f}, "
        f"duration/task={aggregate.average_duration_ms:.0f}ms"
    )
    print(f"Checkpoint written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
