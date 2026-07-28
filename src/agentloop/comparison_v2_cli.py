"""Run the V2 Direct versus validated-Reflection paired pilot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentloop.benchmark import MeteredLLMProvider
from agentloop.benchmark_v2 import (
    DirectStrategyV2,
    ObservableReflectionStrategyV2,
)
from agentloop.config import AppSettings, ConfigurationError
from agentloop.evaluation_agents import (
    EvaluationCoderAgent,
    EvaluationCriticAgent,
    EvaluationTesterAgent,
)
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.evaluation_verifier import EvaluationCodeVerifier
from agentloop.evaluation_workflow import EvaluationReflectionWorkflow
from agentloop.resilient_benchmark import ResilientBenchmarkRunner
from agentloop.sandbox_v2 import DockerSandboxV2
from agentloop.strict_v2_llm import StrictV2OpenAIProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run V2 Direct/Reflection with validated generated suites."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/datasets/coding-v2-pilot.json"),
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
        default=Path("benchmarks/results/direct-vs-reflection-v2-nano.json"),
    )
    parser.add_argument(
        "--trace-dir",
        type=Path,
        default=Path("benchmarks/traces/direct-vs-reflection-v2-nano"),
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
        StrictV2OpenAIProvider(
            api_key=api_key,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
        )
    )
    verifier = EvaluationCodeVerifier(sandbox=DockerSandboxV2())
    direct = DirectStrategyV2(provider=meter, verifier=verifier)
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
        [direct, reflection],
        checkpoint_path=args.output,
    )
    print(
        f"Dataset: {dataset.dataset_id} "
        f"(schema {dataset.schema_version}, {len(dataset.tasks)} paired tasks)"
    )
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
