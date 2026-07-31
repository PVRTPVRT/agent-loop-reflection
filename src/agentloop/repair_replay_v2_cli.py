"""Run a recorded-failure replay against the evidence-driven repair workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentloop.benchmark import MeteredLLMProvider
from agentloop.config import AppSettings, ConfigurationError
from agentloop.contracts_v2 import ContractRegistryV2
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.evaluation_verifier import EvaluationCodeVerifier
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2
from agentloop.normalized_evaluation import NormalizedEvaluationTesterAgent
from agentloop.repair_agents_v2 import (
    RepairEvaluationCoderAgent,
    RepairEvaluationCriticAgent,
)
from agentloop.repair_replay_strategy_v2 import RepairReplayStrategyV2
from agentloop.repair_workflow_v2 import EvidenceDrivenRepairWorkflow
from agentloop.resilient_benchmark import ResilientBenchmarkRunner
from agentloop.role_budget_v2_llm import RoleBudgetV2Provider
from agentloop.routing_suites import RoutingSuiteRegistry
from agentloop.telemetry import TelemetryConfigurationError, telemetry_session


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay a recorded failure through Repair V2."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("benchmarks/datasets/coding-v2-repair-pilot-r2.json"),
    )
    parser.add_argument(
        "--routing",
        type=Path,
        default=Path("benchmarks/routing/coding-v2-repair-routing.json"),
    )
    parser.add_argument(
        "--contracts",
        type=Path,
        default=Path("benchmarks/contracts/coding-v2-repair-contracts.json"),
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        default=Path("benchmarks/fixtures/ttl-lru-expiry-order-bug.py"),
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
        default=Path("benchmarks/results/repair-replay-v0.2-r2.json"),
    )
    parser.add_argument(
        "--trace-dir",
        type=Path,
        default=Path("benchmarks/traces/repair-replay-v0.2-r2"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = AppSettings.from_env()
        api_key = settings.require_api_key()
        dataset = EvaluationDataset.load(args.dataset)
        routing = RoutingSuiteRegistry.load(args.routing)
        contracts = ContractRegistryV2.load(args.contracts)
        recorded_candidate = args.candidate.read_text(encoding="utf-8")
    except (ConfigurationError, OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if len(dataset.tasks) != 1:
        print(
            "Configuration error: repair replay currently requires one dataset task",
            file=sys.stderr,
        )
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
    workflow = EvidenceDrivenRepairWorkflow(
        tester=NormalizedEvaluationTesterAgent(meter, registry=contracts),
        critic=RepairEvaluationCriticAgent(meter, registry=contracts),
        coder=RepairEvaluationCoderAgent(meter, registry=contracts),
        verifier=verifier,
        max_coding_rounds=settings.max_coding_rounds,
    )
    strategy = RepairReplayStrategyV2(
        provider=meter,
        verifier=verifier,
        repair_workflow=workflow,
        routing_suites=routing,
        recorded_candidate=recorded_candidate,
        candidate_source=args.candidate.as_posix(),
        trace_dir=args.trace_dir,
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
        f"repair-replay: {aggregate.passed_tasks}/{aggregate.total_tasks}, "
        f"calls/task={aggregate.average_model_calls:.2f}, "
        f"tokens/task={aggregate.average_total_tokens:.0f}, "
        f"duration/task={aggregate.average_duration_ms:.0f}ms"
    )
    print(f"Checkpoint written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
