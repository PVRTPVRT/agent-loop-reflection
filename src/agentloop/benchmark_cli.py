"""CLI for running Direct vs Reflection benchmark experiments."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentloop.agents import CoderAgent, CriticAgent, TesterAgent
from agentloop.benchmark import (
    BenchmarkRunner,
    DirectStrategy,
    MeteredLLMProvider,
    ReflectionStrategy,
)
from agentloop.benchmark_models import BenchmarkDataset
from agentloop.config import AppSettings, ConfigurationError
from agentloop.llm import OpenAIResponsesProvider
from agentloop.verifier import SandboxCodeVerifier
from agentloop.workflow import ReflectionWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agentloop.benchmark_cli",
        description="Compare Direct and Reflection strategies.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/datasets/coding-v1.json"),
    )
    parser.add_argument(
        "--strategy",
        choices=["direct", "reflection", "both"],
        default="both",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit is not None and args.limit < 1:
        print("配置错误：--limit 必须大于 0", file=sys.stderr)
        return 2
    try:
        settings = AppSettings.from_env().with_model(args.model)
        api_key = settings.require_api_key()
        dataset = BenchmarkDataset.load(args.dataset)
    except (ConfigurationError, OSError, ValueError) as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        return 2

    verifier = SandboxCodeVerifier()
    strategies = []
    if args.strategy in {"direct", "both"}:
        direct_meter = MeteredLLMProvider(
            OpenAIResponsesProvider(
                api_key=api_key,
                default_model=settings.model,
            )
        )
        strategies.append(DirectStrategy(provider=direct_meter, verifier=verifier))
    if args.strategy in {"reflection", "both"}:
        reflection_meter = MeteredLLMProvider(
            OpenAIResponsesProvider(
                api_key=api_key,
                default_model=settings.model,
            )
        )
        workflow = ReflectionWorkflow(
            tester=TesterAgent(reflection_meter),
            critic=CriticAgent(reflection_meter),
            coder=CoderAgent(reflection_meter),
            verifier=verifier,
            max_debate_rounds=settings.max_debate_rounds,
            max_coding_rounds=settings.max_coding_rounds,
        )
        strategies.append(
            ReflectionStrategy(
                workflow=workflow,
                provider=reflection_meter,
                benchmark_verifier=verifier,
            )
        )

    report = BenchmarkRunner().run(
        dataset,
        strategies,
        limit=args.limit,
    )
    for aggregate in report.aggregates:
        print(
            f"{aggregate.strategy}: "
            f"{aggregate.passed_tasks}/{aggregate.total_tasks} "
            f"({aggregate.pass_rate:.1%}), "
            f"calls={aggregate.average_model_calls:.2f}, "
            f"tokens={aggregate.average_total_tokens:.0f}, "
            f"duration={aggregate.average_duration_ms:.0f}ms"
        )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"结果已写入：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
