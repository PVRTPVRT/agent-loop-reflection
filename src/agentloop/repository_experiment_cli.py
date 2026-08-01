"""CLI for the budget-capped repository API pilot."""

from __future__ import annotations

import argparse
import os
from decimal import Decimal
from pathlib import Path

from openai import OpenAI

from agentloop.llm import OpenAIResponsesProvider
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2
from agentloop.repository_benchmark import RepositoryBenchmarkDataset
from agentloop.repository_experiment import (
    NANO_SNAPSHOT,
    REPOSITORY_EDIT_FORMAT,
    BudgetedLLMProvider,
    ModelPrice,
    RepositoryExperimentRunner,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--model", default=NANO_SNAPSHOT)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--max-usd", type=Decimal, default=Decimal("0.10"))
    parser.add_argument("--max-output-tokens", type=int, default=4_000)
    parser.add_argument("--request-timeout", type=float, default=90)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.model != NANO_SNAPSHOT:
        raise SystemExit(f"this pilot has validated pricing only for {NANO_SNAPSHOT}")
    if not Decimal(0) < args.max_usd <= Decimal("0.10"):
        raise SystemExit("--max-usd must be greater than 0 and no more than 0.10")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required")

    dataset = RepositoryBenchmarkDataset.load(args.dataset)
    max_calls = len(dataset.tasks) * args.repetitions * 2
    client = OpenAI(api_key=api_key, timeout=args.request_timeout, max_retries=0)
    provider = BudgetedLLMProvider(
        OpenAIResponsesProvider(
            default_model=args.model,
            reasoning_effort="low",
            text_format=REPOSITORY_EDIT_FORMAT,
            client=client,
        ),
        price=ModelPrice(model=args.model),
        max_usd=args.max_usd,
        max_calls=max_calls,
    )
    workspace_runner = ManagedDockerSandboxV2(timeout_seconds=20)
    workspace_runner.ensure_available()
    report = RepositoryExperimentRunner(
        provider=provider,
        workspace_runner=workspace_runner,
        project_root=Path.cwd(),
        model=args.model,
        max_output_tokens=args.max_output_tokens,
    ).run(
        dataset,
        repetitions=args.repetitions,
        experiment_id=args.experiment_id,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"attempts={len(report.attempts)} calls={provider.calls} "
        f"cost=${report.actual_cost_usd:.6f} stopped_early={report.stopped_early}"
    )
    for aggregate in report.aggregates:
        print(
            f"{aggregate.strategy}: {aggregate.passed}/{aggregate.attempts} passed, "
            f"repair_routes={aggregate.repair_routes}, calls={aggregate.model_calls}"
        )
    return 3 if report.stopped_early else 0


if __name__ == "__main__":
    raise SystemExit(main())
