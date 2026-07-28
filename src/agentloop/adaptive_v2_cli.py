"""Run the bounded adaptive Direct-to-Reflection V2 strategy."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentloop.adaptive_strategy_v2 import AdaptiveStrategyV2
from agentloop.benchmark import MeteredLLMProvider
from agentloop.config import AppSettings, ConfigurationError
from agentloop.evaluation_agents import (
    EvaluationCoderAgent,
    EvaluationCriticAgent,
)
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.evaluation_verifier import EvaluationCodeVerifier
from agentloop.lean_evaluation import LeanNormalizedEvaluationWorkflow
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2
from agentloop.normalized_evaluation import NormalizedEvaluationTesterAgent
from agentloop.resilient_benchmark import ResilientBenchmarkRunner
from agentloop.role_budget_v2_llm import RoleBudgetV2Provider
from agentloop.routing_suites import RoutingSuiteRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run adaptive Direct -> Reflection V2.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/datasets/coding-v2-full.json"),
    )
    parser.add_argument(
        "--routing",
        type=Path,
        default=Path("benchmarks/routing/coding-v2-routing.json"),
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
        default=Path("benchmarks/results/adaptive-v2-nano.json"),
    )
    parser.add_argument(
        "--trace-dir",
        type=Path,
        default=Path("benchmarks/traces/adaptive-v2-nano"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = AppSettings.from_env()
        api_key = settings.require_api_key()
        dataset = EvaluationDataset.load(args.dataset)
        routing = RoutingSuiteRegistry.load(args.routing)
    except (ConfigurationError, OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    meter = MeteredLLMProvider(
        RoleBudgetV2Provider(
            api_key=api_key,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            request_timeout_seconds=args.request_timeout,
            max_retries=args.max_retries,
        )
    )
    verifier = EvaluationCodeVerifier(sandbox=ManagedDockerSandboxV2())
    workflow = LeanNormalizedEvaluationWorkflow(
        tester=NormalizedEvaluationTesterAgent(meter),
        critic=EvaluationCriticAgent(meter),
        coder=EvaluationCoderAgent(meter),
        verifier=verifier,
        max_coding_rounds=settings.max_coding_rounds,
    )
    strategy = AdaptiveStrategyV2(
        provider=meter,
        verifier=verifier,
        reflection_workflow=workflow,
        routing_suites=routing,
        trace_dir=args.trace_dir,
    )
    report = ResilientBenchmarkRunner().run(
        dataset,
        [strategy],
        checkpoint_path=args.output,
    )
    aggregate = report.aggregates[0]
    print(
        f"adaptive: {aggregate.passed_tasks}/{aggregate.total_tasks}, "
        f"calls/task={aggregate.average_model_calls:.2f}, "
        f"tokens/task={aggregate.average_total_tokens:.0f}, "
        f"duration/task={aggregate.average_duration_ms:.0f}ms"
    )
    print(f"Checkpoint written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
