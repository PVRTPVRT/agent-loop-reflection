"""Verify repository patches against trusted fixtures in the managed sandbox."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Protocol

from agentloop.evaluation_boundary import (
    CandidateArtifact,
    EvaluationSpec,
    RepositoryPatchArtifact,
    TestCommandSpec,
    UnsupportedEvaluationBoundaryError,
)
from agentloop.sandbox import ExecutionResult
from agentloop.verifier import VerificationResult

_REPOSITORY_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_IGNORED_FIXTURE_PARTS = frozenset({".git", "__pycache__", ".pytest_cache"})


def _safe_repository_path(raw_path: str) -> str:
    path = PurePosixPath(raw_path)
    if (
        not raw_path
        or "\\" in raw_path
        or path.is_absolute()
        or ".." in path.parts
        or any(part in _IGNORED_FIXTURE_PARTS for part in path.parts)
    ):
        raise ValueError(f"unsafe repository path: {raw_path!r}")
    return path.as_posix()


class RepositoryFixtureError(ValueError):
    """Raised when trusted repository fixture metadata is invalid."""


class WorkspaceRunner(Protocol):
    def execute_workspace(
        self,
        workspace: Path,
        *,
        command: Sequence[str],
        working_directory: str,
        timeout_seconds: int,
        read_only: bool,
    ) -> ExecutionResult:
        """Execute tokenized tests inside a managed container."""


def repository_fingerprint(root: Path) -> str:
    """Hash stable fixture paths and bytes; reject links that could escape the root."""
    resolved = root.resolve()
    if not resolved.is_dir():
        raise RepositoryFixtureError(f"repository fixture does not exist: {resolved}")

    digest = hashlib.sha256()
    files = []
    for path in resolved.rglob("*"):
        relative = path.relative_to(resolved)
        if any(part in _IGNORED_FIXTURE_PARTS for part in relative.parts):
            continue
        if path.is_symlink():
            raise RepositoryFixtureError(
                f"repository fixtures must not contain symlinks: {relative.as_posix()}"
            )
        if path.is_file():
            files.append((relative.as_posix(), path))

    if not files:
        raise RepositoryFixtureError("repository fixture must contain at least one file")
    for relative, path in sorted(files):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class RepositoryFixture:
    repository_id: str
    root: Path
    revision: str
    protected_paths: frozenset[str]

    @classmethod
    def load(
        cls,
        repository_id: str,
        root: str | Path,
        *,
        protected_paths: Sequence[str] = (),
    ) -> RepositoryFixture:
        if not _REPOSITORY_ID.fullmatch(repository_id):
            raise RepositoryFixtureError(
                "repository_id must contain lowercase letters, digits, '.', '_' or '-'"
            )
        if not protected_paths:
            raise RepositoryFixtureError(
                "repository fixtures must declare at least one protected test path"
            )
        resolved = Path(root).resolve()
        normalized_paths = set()
        for raw_path in protected_paths:
            relative_path = _safe_repository_path(raw_path)
            if not resolved.joinpath(*PurePosixPath(relative_path).parts).is_file():
                raise RepositoryFixtureError(
                    f"protected fixture path does not exist: {relative_path}"
                )
            normalized_paths.add(relative_path)
        return cls(
            repository_id=repository_id,
            root=resolved,
            revision=repository_fingerprint(resolved),
            protected_paths=frozenset(normalized_paths),
        )


class RepositoryFixtureRegistry:
    def __init__(self, fixtures: Sequence[RepositoryFixture]) -> None:
        by_id: dict[str, RepositoryFixture] = {}
        for fixture in fixtures:
            if fixture.repository_id in by_id:
                raise RepositoryFixtureError(
                    f"duplicate repository fixture: {fixture.repository_id}"
                )
            by_id[fixture.repository_id] = fixture
        if not by_id:
            raise RepositoryFixtureError("at least one repository fixture is required")
        self._fixtures: Mapping[str, RepositoryFixture] = MappingProxyType(by_id)

    def require(self, repository_id: str, revision: str) -> RepositoryFixture:
        try:
            fixture = self._fixtures[repository_id]
        except KeyError as exc:
            raise RepositoryFixtureError(
                f"unknown repository fixture: {repository_id}"
            ) from exc
        if fixture.revision != revision:
            raise RepositoryFixtureError(
                f"fixture revision mismatch for {repository_id}: "
                f"expected {fixture.revision}, got {revision}"
            )
        return fixture


class RepositoryWorkspaceVerifier:
    """Apply one text patch to a disposable fixture and run its trusted command."""

    def __init__(
        self,
        *,
        runner: WorkspaceRunner,
        fixtures: RepositoryFixtureRegistry,
        git_executable: str = "git",
        patch_timeout_seconds: int = 15,
    ) -> None:
        self.runner = runner
        self.fixtures = fixtures
        self.git_executable = git_executable
        self.patch_timeout_seconds = patch_timeout_seconds

    def verify_artifact(
        self,
        artifact: CandidateArtifact,
        spec: EvaluationSpec,
    ) -> VerificationResult:
        if not isinstance(artifact, RepositoryPatchArtifact):
            raise UnsupportedEvaluationBoundaryError(
                f"repository verifier cannot handle artifact kind {artifact.kind!r}"
            )
        if not isinstance(spec, TestCommandSpec):
            raise UnsupportedEvaluationBoundaryError(
                f"repository verifier cannot handle evaluation kind {spec.kind!r}"
            )

        try:
            fixture = self.fixtures.require(
                artifact.repository_id,
                artifact.base_revision,
            )
            changed_paths = self._validate_patch(artifact.patch)
            protected_changes = sorted(changed_paths & fixture.protected_paths)
            if protected_changes:
                raise ValueError(
                    "candidate patch modifies protected fixture paths: "
                    + ", ".join(protected_changes)
                )
        except ValueError as exc:
            return VerificationResult(success=False, message=str(exc))

        with tempfile.TemporaryDirectory(prefix="agentloop_repo_") as temp_dir:
            temp_root = Path(temp_dir)
            workspace = temp_root / "workspace"
            shutil.copytree(
                fixture.root,
                workspace,
                ignore=shutil.ignore_patterns(*_IGNORED_FIXTURE_PARTS),
            )
            patch_path = temp_root / "candidate.patch"
            patch_path.write_bytes(artifact.patch.encode("utf-8"))

            checked = self._apply_patch(workspace, patch_path, check_only=True)
            if checked is not None:
                return checked
            applied = self._apply_patch(workspace, patch_path, check_only=False)
            if applied is not None:
                return applied

            result = self.runner.execute_workspace(
                workspace,
                command=spec.command,
                working_directory=spec.working_directory,
                timeout_seconds=spec.timeout_seconds,
                read_only=True,
            )
            return VerificationResult(success=result.success, message=result.message)

    def _apply_patch(
        self,
        workspace: Path,
        patch_path: Path,
        *,
        check_only: bool,
    ) -> VerificationResult | None:
        command = [self.git_executable, "apply", "--whitespace=nowarn"]
        if check_only:
            command.append("--check")
        command.append(str(patch_path))
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=self.patch_timeout_seconds,
                encoding="utf-8",
                check=False,
            )
        except (FileNotFoundError, OSError) as exc:
            return VerificationResult(
                success=False,
                message=f"unable to invoke git apply: {exc}",
            )
        except subprocess.TimeoutExpired:
            return VerificationResult(
                success=False,
                message="git apply timed out",
            )
        if completed.returncode == 0:
            return None
        detail = (completed.stderr or completed.stdout).strip()
        return VerificationResult(
            success=False,
            message=f"candidate patch rejected: {detail or 'git apply failed'}",
        )

    @staticmethod
    def _validate_patch(patch: str) -> frozenset[str]:
        if "\0" in patch:
            raise ValueError("repository patch must not contain NUL bytes")
        if "GIT binary patch" in patch:
            raise ValueError("binary repository patches are not supported")
        if re.search(r"^(?:new|old) file mode 120000$", patch, re.MULTILINE):
            raise ValueError("repository patches must not create or modify symlinks")

        changed_paths = set()
        for line in patch.splitlines():
            if not line.startswith(("--- ", "+++ ")):
                continue
            raw_path = line[4:].split("\t", 1)[0].strip()
            if raw_path == "/dev/null":
                continue
            if raw_path.startswith(("a/", "b/")):
                raw_path = raw_path[2:]
            changed_paths.add(_safe_repository_path(raw_path))
        if not changed_paths:
            raise ValueError("repository patch must contain a text-file diff")
        return frozenset(changed_paths)