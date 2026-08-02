import json
from decimal import Decimal
from pathlib import Path

import pytest

from agentloop.evaluation_boundary import RepositoryPatchArtifact
from agentloop.evaluation_boundary import TestCommandSpec as CommandSpec
from agentloop.llm import FakeLLMProvider
from agentloop.models import LLMRequest, LLMResponse, TokenUsage
from agentloop.repository_benchmark import RepositoryBenchmarkDataset
from agentloop.repository_experiment import (
    NANO_SNAPSHOT,
    BudgetedLLMProvider,
    BudgetExceeded,
    ModelPrice,
    RepositoryExperimentRunner,
    render_repository_patch,
)
from agentloop.repository_experiment_cli import build_parser, main
from agentloop.repository_verifier import (
    RepositoryFixture,
    RepositoryFixtureRegistry,
    RepositoryWorkspaceVerifier,
)
from agentloop.sandbox import ExecutionResult

DATASET_PATH = Path("benchmarks/datasets/repository-v0.4.json")
CALCULATOR_SOURCE = '''def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a - b
'''
CALCULATOR_FIX = CALCULATOR_SOURCE.replace("return a - b", "return a + b")
CALCULATOR_NON_FIX = CALCULATOR_SOURCE.replace(
    "Return the sum of two integers.", "Add two signed integers."
)


class SuccessfulRunner:
    def execute_workspace(self, *args, **kwargs) -> ExecutionResult:
        return ExecutionResult(success=True, message="OK", exit_code=0)


class CalculatorRunner:
    def execute_workspace(
        self,
        workspace: Path,
        *,
        command,
        working_directory,
        timeout_seconds,
        read_only,
    ) -> ExecutionResult:
        repaired = "return a + b" in (workspace / "calculator.py").read_text(encoding="utf-8")
        return ExecutionResult(
            success=repaired,
            message="OK" if repaired else "FAILED (failures=1)",
            exit_code=0 if repaired else 1,
        )


def response(text: str, *, input_tokens: int = 100, output_tokens: int = 50) -> LLMResponse:
    return LLMResponse(
        text=text,
        model=NANO_SNAPSHOT,
        usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        ),
    )


def file_set(path: str, content: str) -> str:
    return json.dumps({"files": [{"path": path, "content": content}]})


def calculator_fixture() -> RepositoryFixture:
    return RepositoryFixture.load(
        "calculator-v1",
        "benchmarks/repositories/calculator-v1",
        protected_paths=("test_calculator.py",),
    )


def test_budget_rejects_call_before_provider_can_cross_cap() -> None:
    inner = FakeLLMProvider(["unused"])
    provider = BudgetedLLMProvider(
        inner,
        price=ModelPrice(model=NANO_SNAPSHOT),
        max_usd=Decimal("0.000001"),
        max_calls=1,
    )

    with pytest.raises(BudgetExceeded, match="reserves"):
        provider.generate(
            LLMRequest(
                user_prompt="x",
                model=NANO_SNAPSHOT,
                max_output_tokens=4_000,
            )
        )

    assert inner.requests == []
    assert provider.calls == 0
    assert provider.spent_usd == 0


def test_budget_accounts_usage_at_conservative_uncached_price() -> None:
    provider = BudgetedLLMProvider(
        FakeLLMProvider([response("answer", input_tokens=1_000, output_tokens=500)]),
        price=ModelPrice(model=NANO_SNAPSHOT),
        max_usd=Decimal("0.10"),
        max_calls=1,
    )

    provider.generate(LLMRequest(user_prompt="x", model=NANO_SNAPSHOT, max_output_tokens=1_000))

    assert provider.calls == 1
    assert provider.spent_usd == Decimal("0.00025")


def test_structured_file_replacement_renders_valid_patch() -> None:
    patch = render_repository_patch(
        file_set("calculator.py", CALCULATOR_FIX),
        calculator_fixture(),
    )

    assert patch.startswith("diff --git a/calculator.py b/calculator.py")
    assert "@@ -1,3 +1,3 @@" in patch
    assert "-    return a - b" in patch
    assert "+    return a + b" in patch


def test_structured_file_replacement_normalizes_repository_id_prefix() -> None:
    patch = render_repository_patch(
        file_set("calculator-v1/calculator.py", CALCULATOR_FIX),
        calculator_fixture(),
    )

    assert patch.startswith("diff --git a/calculator.py b/calculator.py")


def test_structured_file_replacement_rejects_protected_test() -> None:
    with pytest.raises(ValueError, match="protected path"):
        render_repository_patch(
            file_set("test_calculator.py", "raise SystemExit\n"),
            calculator_fixture(),
        )


def test_rendered_patch_handles_source_without_final_newline() -> None:
    fixture = RepositoryFixture.load(
        "frame-decoder-v1",
        "benchmarks/repositories/frame-decoder-v1",
        protected_paths=("test_frame_decoder.py",),
    )
    original = (fixture.root / "frame_decoder.py").read_text(encoding="utf-8")
    replacement = original.replace(
        "len(buffer) <= expected_length", "len(buffer) < expected_length"
    )
    patch = render_repository_patch(file_set("frame_decoder.py", replacement), fixture)
    verifier = RepositoryWorkspaceVerifier(
        runner=SuccessfulRunner(),
        fixtures=RepositoryFixtureRegistry((fixture,)),
    )

    result = verifier.verify_artifact(
        RepositoryPatchArtifact(
            repository_id=fixture.repository_id,
            base_revision=fixture.revision,
            patch=patch,
        ),
        CommandSpec(command=("python", "-B", "-m", "unittest", "-q")),
    )

    assert "\\ No newline at end of file" in patch
    assert result.success is True


def test_repository_experiment_routes_failed_adaptive_patch_to_one_repair() -> None:
    dataset = RepositoryBenchmarkDataset.load(DATASET_PATH)
    calculator_only = dataset.model_copy(update={"tasks": (dataset.tasks[0],)})
    inner = FakeLLMProvider(
        [
            response(file_set("calculator.py", CALCULATOR_NON_FIX)),
            response(file_set("calculator.py", CALCULATOR_FIX)),
        ]
    )
    provider = BudgetedLLMProvider(
        inner,
        price=ModelPrice(model=NANO_SNAPSHOT),
        max_usd=Decimal("0.10"),
        max_calls=2,
    )

    report = RepositoryExperimentRunner(
        provider=provider,
        workspace_runner=CalculatorRunner(),
        project_root=Path.cwd(),
    ).run(calculator_only, repetitions=1, experiment_id="test")

    assert [attempt.strategy for attempt in report.attempts] == ["direct", "adaptive"]
    assert [attempt.success for attempt in report.attempts] == [False, True]
    assert report.schema_version == "1.2"
    assert report.paired_initial_candidates is True
    assert report.strategy_cost_accounting == "counterfactual_attribution"
    assert report.attempts[0].initial_patch == report.attempts[1].initial_patch
    assert report.attempts[0].initial_patch_sha256 == report.attempts[1].initial_patch_sha256
    assert report.attempts[1].initial_success is False
    assert report.attempts[1].repair_triggered is True
    assert report.attempts[1].model_calls == 2
    assert [aggregate.passed for aggregate in report.aggregates] == [0, 1]
    prompts = "\n".join(request.user_prompt for request in inner.requests)
    assert "test_calculator.py" not in prompts
    assert "FAILED (failures=1)" in inner.requests[-1].user_prompt


def test_repository_experiment_cli_defaults_are_budget_capped() -> None:
    args = build_parser().parse_args(
        ["--dataset", "dataset.json", "--output", "result.json", "--experiment-id", "x"]
    )

    assert args.model == NANO_SNAPSHOT
    assert args.max_usd == Decimal("0.10")
    assert args.repetitions == 3


def test_repository_experiment_cli_rejects_unpriced_model() -> None:
    with pytest.raises(SystemExit, match="validated pricing"):
        main(
            [
                "--dataset",
                "dataset.json",
                "--output",
                "result.json",
                "--experiment-id",
                "x",
                "--model",
                "unpriced-model",
            ]
        )


def test_repository_experiment_cli_requires_key_without_exposing_it(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="OPENAI_API_KEY is required"):
        main(["--dataset", "dataset.json", "--output", "result.json", "--experiment-id", "x"])
