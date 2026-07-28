"""Low-cost portability benchmark with explicit reasoning controls."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentloop.agents import CoderAgent, CriticAgent, TesterAgent
from agentloop.benchmark import (
    BenchmarkRunner,
    MeteredLLMProvider,
    ReflectionStrategy,
)
from agentloop.benchmark_models import BenchmarkDataset
from agentloop.config import AppSettings, ConfigurationError
from agentloop.portable_llm import PortableOpenAIProvider
from agentloop.verifier import SandboxCodeVerifier
from agentloop.workflow import ReflectionWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a low-cost Reflection portability smoke test."
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
        default="low",
    )
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit < 1:
        print("配置错误：--limit 必须大于 0", file=sys.stderr)
        return 2
    try:
        settings = AppSettings.from_env()
        api_key = settings.require_api_key()
        dataset = BenchmarkDataset.load(args.dataset)
    except (ConfigurationError, OSError, ValueError) as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        return 2

    meter = MeteredLLMProvider(
        PortableOpenAIProvider(
            api_key=api_key,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
        )
    )
    verifier = SandboxCodeVerifier()
    workflow = ReflectionWorkflow(
        tester=TesterAgent(meter),
        critic=CriticAgent(meter),
        coder=CoderAgent(meter),
        verifier=verifier,
        max_debate_rounds=settings.max_debate_rounds,
        max_coding_rounds=settings.max_coding_rounds,
    )
    strategy = ReflectionStrategy(
        workflow=workflow,
        provider=meter,
        benchmark_verifier=verifier,
    )
    report = BenchmarkRunner().run(dataset, [strategy], limit=args.limit)
    aggregate = report.aggregates[0]
    print(
        f"{args.model}/{args.reasoning_effort}: "
        f"{aggregate.passed_tasks}/{aggregate.total_tasks}, "
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
