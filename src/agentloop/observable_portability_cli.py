"""Run a grounded, fully observable Reflection portability experiment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentloop.agents import CoderAgent
from agentloop.benchmark import MeteredLLMProvider
from agentloop.benchmark_models import BenchmarkDataset
from agentloop.config import AppSettings, ConfigurationError
from agentloop.grounded_agents import GroundedCriticAgent, GroundedTesterAgent
from agentloop.observable_benchmark import ObservableReflectionStrategy
from agentloop.resilient_benchmark import ResilientBenchmarkRunner
from agentloop.strict_json_llm import StrictJSONOpenAIProvider
from agentloop.verifier import SandboxCodeVerifier
from agentloop.workflow import ReflectionWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run grounded Reflection and persist its internal trace."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/datasets/coding-v1.json"),
    )
    parser.add_argument("--model", default="gpt-5.4-nano")
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high"],
        default="none",
    )
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/results/reflection-observable-gpt-5.4-nano.json"),
    )
    parser.add_argument(
        "--trace-dir",
        type=Path,
        default=Path("benchmarks/traces/reflection-observable-gpt-5.4-nano"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit < 1:
        print("Configuration error: --limit must be greater than zero.", file=sys.stderr)
        return 2
    try:
        settings = AppSettings.from_env()
        api_key = settings.require_api_key()
        dataset = BenchmarkDataset.load(args.dataset)
    except (ConfigurationError, OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    meter = MeteredLLMProvider(
        StrictJSONOpenAIProvider(
            api_key=api_key,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
        )
    )
    verifier = SandboxCodeVerifier()
    workflow = ReflectionWorkflow(
        tester=GroundedTesterAgent(meter),
        critic=GroundedCriticAgent(meter),
        coder=CoderAgent(meter),
        verifier=verifier,
        max_debate_rounds=settings.max_debate_rounds,
        max_coding_rounds=settings.max_coding_rounds,
    )
    strategy = ObservableReflectionStrategy(
        workflow=workflow,
        provider=meter,
        benchmark_verifier=verifier,
        trace_dir=args.trace_dir,
    )
    report = ResilientBenchmarkRunner().run(
        dataset,
        [strategy],
        limit=args.limit,
        checkpoint_path=args.output,
    )
    aggregate = report.aggregates[0]
    print(
        f"{args.model}/{args.reasoning_effort}: "
        f"{aggregate.passed_tasks}/{aggregate.total_tasks}, "
        f"calls={aggregate.average_model_calls:.2f}, "
        f"tokens={aggregate.average_total_tokens:.0f}, "
        f"duration={aggregate.average_duration_ms:.0f}ms"
    )
    print(f"Checkpoint written: {args.output}")
    print(f"Internal traces written under: {args.trace_dir}")
    return 0 if aggregate.passed_tasks == aggregate.total_tasks else 1


if __name__ == "__main__":
    raise SystemExit(main())
