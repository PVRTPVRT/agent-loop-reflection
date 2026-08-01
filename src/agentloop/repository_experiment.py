"""Budget-capped Direct versus Adaptive repository repair experiment."""

from __future__ import annotations

import difflib
import hashlib
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentloop.evaluation_boundary import RepositoryPatchArtifact
from agentloop.llm import LLMProvider
from agentloop.models import LLMRequest, LLMResponse
from agentloop.repository_benchmark import (
    RepositoryBenchmarkDataset,
    RepositoryBenchmarkTask,
)
from agentloop.repository_verifier import (
    RepositoryFixture,
    RepositoryFixtureError,
    RepositoryFixtureRegistry,
    RepositoryWorkspaceVerifier,
    WorkspaceRunner,
)
from agentloop.verifier import VerificationResult

NANO_SNAPSHOT = "gpt-5-nano-2025-08-07"
REPOSITORY_EDIT_FORMAT = {
    "type": "json_schema",
    "name": "repository_file_edits",
    "description": "Complete replacement content for each repository file that must change.",
    "schema": {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "minLength": 1},
                        "content": {"type": "string", "minLength": 1},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["files"],
        "additionalProperties": False,
    },
    "strict": True,
}


class ExperimentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RepositoryFileEdit(ExperimentModel):
    path: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=131_072)


class RepositoryFileSet(ExperimentModel):
    files: tuple[RepositoryFileEdit, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_paths(self) -> RepositoryFileSet:
        paths = [edit.path for edit in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("repository file edit paths must be unique")
        return self


class ModelPrice(ExperimentModel):
    model: str
    input_usd_per_million: Decimal = Decimal("0.05")
    output_usd_per_million: Decimal = Decimal("0.40")

    def cost(self, *, input_tokens: int, output_tokens: int) -> Decimal:
        million = Decimal(1_000_000)
        return (
            Decimal(input_tokens) * self.input_usd_per_million
            + Decimal(output_tokens) * self.output_usd_per_million
        ) / million


class BudgetExceeded(RuntimeError):
    """Raised before an API call that could cross the configured hard cap."""


class BudgetedLLMProvider:
    """Apply a call limit and conservative per-call dollar reservation."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        price: ModelPrice,
        max_usd: Decimal,
        max_calls: int,
    ) -> None:
        if max_usd <= 0 or max_calls < 1:
            raise ValueError("budget and call limit must be positive")
        self.provider = provider
        self.price = price
        self.max_usd = max_usd
        self.max_calls = max_calls
        self.calls = 0
        self.spent_usd = Decimal(0)

    @staticmethod
    def _input_token_upper_bound(request: LLMRequest) -> int:
        prompt_bytes = len(request.system_prompt.encode("utf-8")) + len(
            request.user_prompt.encode("utf-8")
        )
        return prompt_bytes + 1_024

    def reservation(self, request: LLMRequest) -> Decimal:
        return self.price.cost(
            input_tokens=self._input_token_upper_bound(request),
            output_tokens=request.max_output_tokens,
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        if (request.model or self.price.model) != self.price.model:
            raise ValueError("request model does not match the configured price")
        if self.calls >= self.max_calls:
            raise BudgetExceeded(f"API call limit reached ({self.max_calls})")
        reserved = self.reservation(request)
        if self.spent_usd + reserved > self.max_usd:
            raise BudgetExceeded(
                f"next call reserves ${reserved:.6f}; "
                f"${self.spent_usd:.6f} already spent of ${self.max_usd:.2f}"
            )

        response = self.provider.generate(request)
        actual = self.price.cost(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        self.calls += 1
        self.spent_usd += actual
        if actual > reserved:
            raise RuntimeError("provider usage exceeded the conservative call reservation")
        return response


class RepositoryExperimentAttempt(ExperimentModel):
    task_id: str
    difficulty: str
    strategy: Literal["direct", "adaptive"]
    repetition: int = Field(ge=1)
    path: Literal["direct", "repair"]
    initial_success: bool
    repair_triggered: bool
    success: bool
    model_calls: int = Field(ge=1)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=0)
    duration_ms: float = Field(ge=0)
    message: str
    initial_patch_sha256: str
    final_patch_sha256: str
    initial_patch: str | None = None
    final_patch: str | None = None


class RepositoryExperimentAggregate(ExperimentModel):
    strategy: Literal["direct", "adaptive"]
    attempts: int
    passed: int
    pass_rate: float
    repair_routes: int
    model_calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal


class RepositoryExperimentReport(ExperimentModel):
    schema_version: Literal["1.2"] = "1.2"
    experiment_id: str
    created_at: str
    dataset_id: str
    dataset_fingerprint: str
    model_price: ModelPrice
    paired_initial_candidates: Literal[True]
    strategy_cost_accounting: Literal["counterfactual_attribution"]
    repetitions: int
    max_budget_usd: Decimal
    actual_cost_usd: Decimal
    stopped_early: bool
    stop_reason: str = ""
    attempts: tuple[RepositoryExperimentAttempt, ...]
    aggregates: tuple[RepositoryExperimentAggregate, ...]


def _patch_sha256(patch: str) -> str:
    return hashlib.sha256(patch.encode("utf-8")).hexdigest()


def _render_unified_diff(original: str, replacement: str, relative: str) -> str:
    lines = difflib.unified_diff(
        original.splitlines(keepends=True),
        replacement.splitlines(keepends=True),
        fromfile=f"a/{relative}",
        tofile=f"b/{relative}",
    )
    rendered = []
    for line in lines:
        rendered.append(line)
        if not line.endswith("\n"):
            rendered.append("\n\\ No newline at end of file\n")
    return "".join(rendered)


def render_repository_patch(text: str, fixture: RepositoryFixture) -> str:
    """Validate structured file replacements and deterministically render a patch."""
    edits = RepositoryFileSet.model_validate_json(text)
    patches = []
    for edit in edits.files:
        path = PurePosixPath(edit.path)
        if (
            "\\" in edit.path
            or path.is_absolute()
            or ".." in path.parts
            or any(part in {".git", "__pycache__"} for part in path.parts)
        ):
            raise ValueError(f"unsafe model file path: {edit.path!r}")
        if len(path.parts) > 1 and path.parts[0] == fixture.repository_id:
            path = PurePosixPath(*path.parts[1:])
        relative = path.as_posix()
        if relative in fixture.protected_paths:
            raise ValueError(f"model attempted to replace protected path: {relative}")
        source_path = fixture.root.joinpath(*path.parts)
        if not source_path.is_file():
            raise ValueError(f"model may only replace existing files: {relative}")

        original = source_path.read_text(encoding="utf-8")
        replacement = edit.content
        if not replacement.endswith("\n"):
            replacement += "\n"
        if replacement == original:
            continue
        diff = _render_unified_diff(original, replacement, relative)
        patches.append(f"diff --git a/{relative} b/{relative}\n{diff}")
    if not patches:
        raise ValueError("model file replacements did not change the repository")
    return "".join(patches)


def _visible_repository(fixture: RepositoryFixture) -> str:
    blocks = []
    for path in sorted(fixture.root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(fixture.root).as_posix()
        if relative in fixture.protected_paths:
            continue
        blocks.append(f"### {relative}\n```\n{path.read_text(encoding='utf-8')}\n```")
    if not blocks:
        raise RepositoryFixtureError("fixture has no model-visible source files")
    return "\n\n".join(blocks)


def _direct_request(
    task: RepositoryBenchmarkTask,
    fixture: RepositoryFixture,
    *,
    model: str,
    max_output_tokens: int,
    repetition: int,
    strategy: str,
) -> LLMRequest:
    return LLMRequest(
        system_prompt=(
            "You repair small Python repositories. Use the response schema to return complete "
            "replacement content only for files that must change. Never modify tests."
        ),
        user_prompt=(
            f"Task:\n{task.prompt}\n\n"
            f"Repository: {fixture.repository_id}\nBase revision: {fixture.revision}\n\n"
            f"Model-visible files (protected tests are intentionally hidden):\n"
            f"{_visible_repository(fixture)}\n\n"
            "Use paths exactly as shown, without a repository-id prefix, and preserve public behavior."
        ),
        model=model,
        max_output_tokens=max_output_tokens,
        metadata={
            "agent": "repository_direct",
            "strategy": strategy,
            "task_id": task.task_id,
            "repetition": str(repetition),
        },
    )


def _repair_request(
    task: RepositoryBenchmarkTask,
    fixture: RepositoryFixture,
    *,
    previous_patch: str,
    verification_message: str,
    model: str,
    max_output_tokens: int,
    repetition: int,
) -> LLMRequest:
    return LLMRequest(
        system_prompt=(
            "You are the repair stage of an adaptive coding agent. Diagnose the failed candidate "
            "from the evidence, then use the response schema to return complete replacement "
            "content only for files that must change. Never modify tests."
        ),
        user_prompt=(
            f"Task:\n{task.prompt}\n\n"
            f"Verifier evidence:\n{verification_message}\n\n"
            f"Previous patch:\n{previous_patch or '<no valid patch>'}\n\n"
            f"Original model-visible files:\n{_visible_repository(fixture)}"
        ),
        model=model,
        max_output_tokens=max_output_tokens,
        metadata={
            "agent": "repository_repair",
            "strategy": "adaptive",
            "task_id": task.task_id,
            "repetition": str(repetition),
        },
    )


def _verify_response(
    response: LLMResponse,
    *,
    fixture: RepositoryFixture,
    task: RepositoryBenchmarkTask,
    verifier: RepositoryWorkspaceVerifier,
) -> tuple[str, VerificationResult]:
    try:
        patch = render_repository_patch(response.text, fixture)
    except ValueError as exc:
        return "", VerificationResult(success=False, message=str(exc))
    result = verifier.verify_artifact(
        RepositoryPatchArtifact(
            repository_id=fixture.repository_id,
            base_revision=fixture.revision,
            patch=patch,
        ),
        task.evaluation,
    )
    return patch, result


class RepositoryExperimentRunner:
    def __init__(
        self,
        *,
        provider: BudgetedLLMProvider,
        workspace_runner: WorkspaceRunner,
        project_root: Path,
        model: str = NANO_SNAPSHOT,
        max_output_tokens: int = 4_000,
    ) -> None:
        self.provider = provider
        self.workspace_runner = workspace_runner
        self.project_root = project_root.resolve()
        self.model = model
        self.max_output_tokens = max_output_tokens

    def run(
        self,
        dataset: RepositoryBenchmarkDataset,
        *,
        repetitions: int,
        experiment_id: str,
    ) -> RepositoryExperimentReport:
        if repetitions < 1:
            raise ValueError("repetitions must be positive")
        fixtures = self._load_fixtures(dataset)
        verifier = RepositoryWorkspaceVerifier(
            runner=self.workspace_runner,
            fixtures=RepositoryFixtureRegistry(tuple(fixtures.values())),
        )
        attempts: list[RepositoryExperimentAttempt] = []
        stop_reason = ""
        try:
            for repetition in range(1, repetitions + 1):
                for task in dataset.tasks:
                    fixture = fixtures[task.repository_id]
                    attempts.extend(
                        self._run_pair(
                            task,
                            fixture,
                            verifier=verifier,
                            repetition=repetition,
                        )
                    )
        except BudgetExceeded as exc:
            stop_reason = str(exc)

        return RepositoryExperimentReport(
            experiment_id=experiment_id,
            created_at=datetime.now(UTC).isoformat(),
            dataset_id=dataset.dataset_id,
            dataset_fingerprint=dataset.fingerprint,
            model_price=self.provider.price,
            paired_initial_candidates=True,
            strategy_cost_accounting="counterfactual_attribution",
            repetitions=repetitions,
            max_budget_usd=self.provider.max_usd,
            actual_cost_usd=self.provider.spent_usd,
            stopped_early=bool(stop_reason),
            stop_reason=stop_reason,
            attempts=tuple(attempts),
            aggregates=self._aggregate(attempts),
        )

    def _load_fixtures(self, dataset: RepositoryBenchmarkDataset) -> dict[str, RepositoryFixture]:
        fixtures = {}
        for task in dataset.tasks:
            root = self.project_root.joinpath(*PurePosixPath(task.fixture_path).parts)
            fixture = RepositoryFixture.load(
                task.repository_id,
                root,
                protected_paths=task.protected_paths,
            )
            if fixture.revision != task.fixture_revision:
                raise RepositoryFixtureError(
                    f"dataset fixture revision is stale for {task.repository_id}"
                )
            fixtures[task.repository_id] = fixture
        return fixtures

    def _run_pair(
        self,
        task: RepositoryBenchmarkTask,
        fixture: RepositoryFixture,
        *,
        verifier: RepositoryWorkspaceVerifier,
        repetition: int,
    ) -> tuple[RepositoryExperimentAttempt, RepositoryExperimentAttempt]:
        started = time.perf_counter()
        direct = self.provider.generate(
            _direct_request(
                task,
                fixture,
                model=self.model,
                max_output_tokens=self.max_output_tokens,
                repetition=repetition,
                strategy="paired",
            )
        )
        initial_patch, initial_result = _verify_response(
            direct,
            fixture=fixture,
            task=task,
            verifier=verifier,
        )
        direct_duration_ms = (time.perf_counter() - started) * 1_000
        direct_cost = self.provider.price.cost(
            input_tokens=direct.usage.input_tokens,
            output_tokens=direct.usage.output_tokens,
        )
        direct_attempt = RepositoryExperimentAttempt(
            task_id=task.task_id,
            difficulty=task.difficulty,
            strategy="direct",
            repetition=repetition,
            path="direct",
            initial_success=initial_result.success,
            repair_triggered=False,
            success=initial_result.success,
            model_calls=1,
            input_tokens=direct.usage.input_tokens,
            output_tokens=direct.usage.output_tokens,
            cost_usd=direct_cost,
            duration_ms=direct_duration_ms,
            message=initial_result.message,
            initial_patch_sha256=_patch_sha256(initial_patch),
            final_patch_sha256=_patch_sha256(initial_patch),
            initial_patch=None if initial_result.success else initial_patch,
            final_patch=None if initial_result.success else initial_patch,
        )
        if initial_result.success:
            adaptive_attempt = direct_attempt.model_copy(update={"strategy": "adaptive"})
            return direct_attempt, adaptive_attempt

        repair = self.provider.generate(
            _repair_request(
                task,
                fixture,
                previous_patch=initial_patch,
                verification_message=initial_result.message,
                model=self.model,
                max_output_tokens=self.max_output_tokens,
                repetition=repetition,
            )
        )
        final_patch, final_result = _verify_response(
            repair,
            fixture=fixture,
            task=task,
            verifier=verifier,
        )
        repair_cost = self.provider.price.cost(
            input_tokens=repair.usage.input_tokens,
            output_tokens=repair.usage.output_tokens,
        )
        adaptive_attempt = RepositoryExperimentAttempt(
            task_id=task.task_id,
            difficulty=task.difficulty,
            strategy="adaptive",
            repetition=repetition,
            path="repair",
            initial_success=False,
            repair_triggered=True,
            success=final_result.success,
            model_calls=2,
            input_tokens=direct.usage.input_tokens + repair.usage.input_tokens,
            output_tokens=direct.usage.output_tokens + repair.usage.output_tokens,
            cost_usd=direct_cost + repair_cost,
            duration_ms=(time.perf_counter() - started) * 1_000,
            message=final_result.message,
            initial_patch_sha256=_patch_sha256(initial_patch),
            final_patch_sha256=_patch_sha256(final_patch),
            initial_patch=initial_patch,
            final_patch=final_patch,
        )
        return direct_attempt, adaptive_attempt

    @staticmethod
    def _aggregate(
        attempts: Sequence[RepositoryExperimentAttempt],
    ) -> tuple[RepositoryExperimentAggregate, ...]:
        aggregates = []
        for strategy in ("direct", "adaptive"):
            selected = [attempt for attempt in attempts if attempt.strategy == strategy]
            if not selected:
                continue
            aggregates.append(
                RepositoryExperimentAggregate(
                    strategy=strategy,
                    attempts=len(selected),
                    passed=sum(attempt.success for attempt in selected),
                    pass_rate=sum(attempt.success for attempt in selected) / len(selected),
                    repair_routes=sum(attempt.repair_triggered for attempt in selected),
                    model_calls=sum(attempt.model_calls for attempt in selected),
                    input_tokens=sum(attempt.input_tokens for attempt in selected),
                    output_tokens=sum(attempt.output_tokens for attempt in selected),
                    cost_usd=sum((attempt.cost_usd for attempt in selected), Decimal(0)),
                )
            )
        return tuple(aggregates)
