"""Paired Direct versus contract-grounded Reflection pilot experiment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentloop.agents import CoderAgent
from agentloop.benchmark import DirectStrategy, MeteredLLMProvider
from agentloop.benchmark_models import BenchmarkDataset
from agentloop.config import AppSettings, ConfigurationError
from agentloop.contract_agents import ContractCriticAgent, ContractTesterAgent
from agentloop.observable_benchmark import ObservableReflectionStrategy
from agentloop.resilient_benchmark import ResilientBenchmarkRunner
from agentloop.strict_json_llm import StrictJSONOpenAIProvider
from agentloop.verifier import SandboxCodeVerifier
from agentloop.workflow import ReflectionWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a paired Direct/Reflection pilot on representative tasks."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/datasets/coding-v1-pilot.json"),
    )
    parser.add_argument("--model", default="gpt-5.4-nano")
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high"],
        default="none",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/results/direct-vs-reflection-pilot-nano.json"),
    )
    parser.add_argument(
        "--trace-dir",
        type=Path,
        default=Path("benchmarks/traces/direct-vs-reflection-pilot-nano"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = AppSettings.from_env()
        api_key = settings.require_api_key()
        dataset = BenchmarkDataset.load(args.dataset)
    except (ConfigurationError, OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    provider = StrictJSONOpenAIProvider(
        api_key=api_key,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
    )
    meter = MeteredLLMProvider(provider)
    verifier = SandboxCodeVerifier()
    direct = DirectStrategy(provider=meter, verifier=verifier)
    workflow = ReflectionWorkflow(
        tester=ContractTesterAgent(meter),
        critic=ContractCriticAgent(meter),
        coder=CoderAgent(meter),
        verifier=verifier,
        max_debate_rounds=settings.max_debate_rounds,
        max_coding_rounds=settings.max_coding_rounds,
    )
    reflection = ObservableReflectionStrategy(
        workflow=workflow,
        provider=meter,
        benchmark_verifier=verifier,
        trace_dir=args.trace_dir,
    )
    report = ResilientBenchmarkRunner().run(
        dataset,
        [direct, reflection],
        checkpoint_path=args.output,
    )

    print(f"Dataset: {dataset.dataset_id} ({len(dataset.tasks)} paired tasks)")
    for aggregate in report.aggregates:
        print(
            f"{aggregate.strategy}: "
            f"{aggregate.passed_tasks}/{aggregate.total_tasks}, "
            f"pass_rate={aggregate.pass_rate:.0%}, "
            f"calls/task={aggregate.average_model_calls:.2f}, "
            f"tokens/task={aggregate.average_total_tokens:.0f}, "
            f"duration/task={aggregate.average_duration_ms:.0f}ms"
        )
    print(f"Checkpoint written: {args.output}")
    print(f"Reflection traces written under: {args.trace_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
