"""Typed boundary between generated artifacts and their evaluation specifications."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentloop.evaluation_v2_models import EvaluationSuite

if TYPE_CHECKING:
    from agentloop.verifier import VerificationResult


class EvaluationBoundaryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceCodeArtifact(EvaluationBoundaryModel):
    kind: Literal["source_code"] = "source_code"
    language: Literal["python"] = "python"
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def require_executable_content(cls, content: str) -> str:
        if not content.strip():
            raise ValueError("failed_code/source content must not be blank")
        return content


class RepositoryPatchArtifact(EvaluationBoundaryModel):
    kind: Literal["repository_patch"] = "repository_patch"
    repository_id: str = Field(
        min_length=1,
        pattern=r"^[a-z0-9][a-z0-9._-]*$",
    )
    base_revision: str = Field(min_length=1)
    patch: str = Field(min_length=1, max_length=262_144)

    @field_validator("repository_id", "base_revision")
    @classmethod
    def require_repository_metadata(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("repository metadata must not be blank")
        return value

    @field_validator("patch")
    @classmethod
    def require_patch_content(cls, patch: str) -> str:
        if not patch.strip():
            raise ValueError("repository patch must not be blank")
        return patch


CandidateArtifact = Annotated[
    SourceCodeArtifact | RepositoryPatchArtifact,
    Field(discriminator="kind"),
]


class FunctionCaseSpec(EvaluationBoundaryModel):
    kind: Literal["function_cases"] = "function_cases"
    suite: EvaluationSuite


class TestCommandSpec(EvaluationBoundaryModel):
    kind: Literal["test_command"] = "test_command"
    command: tuple[str, ...] = Field(min_length=1)
    working_directory: str = "."
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    network_enabled: Literal[False] = False

    @field_validator("command")
    @classmethod
    def require_command_tokens(cls, command: tuple[str, ...]) -> tuple[str, ...]:
        if any(not token.strip() for token in command):
            raise ValueError("test command tokens must not be blank")
        return command

    @field_validator("working_directory")
    @classmethod
    def require_relative_working_directory(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("working_directory must not be blank")
        normalized = value.replace("\\", "/")
        posix_path = PurePosixPath(normalized)
        windows_path = PureWindowsPath(value)
        escapes_workspace = (
            posix_path.is_absolute()
            or windows_path.is_absolute()
            or bool(windows_path.drive)
            or ".." in posix_path.parts
        )
        if escapes_workspace:
            raise ValueError("working_directory must stay inside the candidate workspace")
        return value


EvaluationSpec = Annotated[
    FunctionCaseSpec | TestCommandSpec,
    Field(discriminator="kind"),
]


class ArtifactVerifier(Protocol):
    def verify_artifact(
        self,
        artifact: CandidateArtifact,
        spec: EvaluationSpec,
    ) -> VerificationResult:
        """Verify a typed artifact against a typed specification."""


class UnsupportedEvaluationBoundaryError(ValueError):
    """Raised when a verifier cannot evaluate an artifact/specification pair."""


def source_code_artifact(code: str) -> SourceCodeArtifact:
    return SourceCodeArtifact(content=code)


def function_case_spec(suite: EvaluationSuite) -> FunctionCaseSpec:
    return FunctionCaseSpec(suite=suite)


def require_source_code(artifact: CandidateArtifact) -> str:
    if not isinstance(artifact, SourceCodeArtifact):
        raise UnsupportedEvaluationBoundaryError(
            f"source-code workflow cannot handle artifact kind {artifact.kind!r}"
        )
    return artifact.content


def require_function_suite(spec: EvaluationSpec) -> EvaluationSuite:
    if not isinstance(spec, FunctionCaseSpec):
        raise UnsupportedEvaluationBoundaryError(
            f"function verifier cannot handle evaluation kind {spec.kind!r}"
        )
    return spec.suite


def verify_artifact(
    verifier: Any,
    artifact: CandidateArtifact,
    spec: EvaluationSpec,
) -> VerificationResult:
    generic_verify = getattr(verifier, "verify_artifact", None)
    if callable(generic_verify):
        return generic_verify(artifact, spec)
    return verifier.verify(
        require_source_code(artifact),
        require_function_suite(spec),
    )
