"""Managed Docker lifecycle shared by function and repository verification."""

from __future__ import annotations

import subprocess
import tempfile
import uuid
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from agentloop.sandbox import ExecutionResult, SandboxUnavailableError
from agentloop.sandbox_v2 import DockerSandboxV2


class ManagedDockerSandboxV2(DockerSandboxV2):
    """Run tokenized commands in named containers and always remove them."""

    def __init__(self, *, timeout_seconds: int = 15, **kwargs) -> None:
        super().__init__(timeout_seconds=timeout_seconds, **kwargs)

    def execute_v2(
        self,
        code: str,
        test_suite: dict[str, Any],
    ) -> ExecutionResult:
        runner_content = self._build_v2_runner_script(code, test_suite)
        with tempfile.TemporaryDirectory(prefix="agentloop_managed_v2_") as temp_dir:
            workspace = Path(temp_dir)
            self._write_runner_script(workspace, runner_content)
            return self.execute_workspace(
                workspace,
                command=("python", "-B", "/workspace/runner.py"),
                working_directory=".",
                timeout_seconds=self.timeout_seconds,
                read_only=True,
                error_parser=self._parse_v2_stderr,
            )

    def execute_workspace(
        self,
        workspace: Path,
        *,
        command: Sequence[str],
        working_directory: str,
        timeout_seconds: int,
        read_only: bool,
        error_parser: Callable[[str], str] | None = None,
    ) -> ExecutionResult:
        """Execute a direct argv vector inside one resource-limited container."""
        if not command or any(not token.strip() for token in command):
            raise ValueError("container command tokens must not be blank")
        if not 1 <= timeout_seconds <= 600:
            raise ValueError("container timeout must be between 1 and 600 seconds")
        resolved_workspace = workspace.resolve()
        if workspace.is_symlink() or not resolved_workspace.is_dir():
            raise ValueError("container workspace must be an existing directory")
        container_workdir = self._container_workdir(working_directory)
        self.ensure_available()
        name = f"agentloop-{uuid.uuid4().hex[:12]}"

        try:
            create = subprocess.run(
                self._build_create_command(
                    name,
                    resolved_workspace,
                    command=command,
                    container_workdir=container_workdir,
                    read_only=read_only,
                ),
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                check=False,
            )
            if create.returncode != 0:
                raise SandboxUnavailableError(
                    f"Docker create failed: "
                    f"{create.stderr.strip() or create.stdout.strip()}"
                )

            start = subprocess.run(
                ["docker", "start", name],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                check=False,
            )
            if start.returncode != 0:
                raise SandboxUnavailableError(
                    f"Docker start failed: {start.stderr.strip()}"
                )

            try:
                waited = subprocess.run(
                    ["docker", "wait", name],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    encoding="utf-8",
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    success=False,
                    message=f"Execution timed out after {timeout_seconds}s",
                )

            logs = subprocess.run(
                ["docker", "logs", name],
                capture_output=True,
                text=True,
                timeout=15,
                encoding="utf-8",
                check=False,
            )
            stdout = logs.stdout.strip()
            stderr = logs.stderr.strip()
            try:
                exit_code = int(waited.stdout.strip())
            except ValueError:
                exit_code = 1
            if exit_code == 0:
                return ExecutionResult(
                    success=True,
                    message=stdout or "Command completed successfully",
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                )
            message = (
                error_parser(stderr)
                if error_parser is not None
                else self._parse_command_failure(stdout, stderr)
            )
            return ExecutionResult(
                success=False,
                message=message,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
            )
        finally:
            subprocess.run(
                ["docker", "rm", "-f", name],
                capture_output=True,
                text=True,
                timeout=15,
                encoding="utf-8",
                check=False,
            )

    def _build_create_command(
        self,
        name: str,
        workspace: Path,
        *,
        command: Sequence[str],
        container_workdir: str,
        read_only: bool,
    ) -> list[str]:
        mount_mode = "ro" if read_only else "rw"
        return [
            "docker",
            "create",
            "--name",
            name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            self.memory_limit,
            "--cpus",
            self.cpu_limit,
            "--pids-limit",
            str(self.pids_limit),
            "--user",
            "65534:65534",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=16m",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--volume",
            f"{workspace}:/workspace:{mount_mode}",
            "--workdir",
            container_workdir,
            self.image,
            *command,
        ]

    @staticmethod
    def _container_workdir(working_directory: str) -> str:
        if not working_directory.strip():
            raise ValueError("working_directory must not be blank")
        normalized = working_directory.replace("\\", "/")
        relative = PurePosixPath(normalized)
        windows_path = PureWindowsPath(working_directory)
        if (
            relative.is_absolute()
            or windows_path.is_absolute()
            or bool(windows_path.drive)
            or ".." in relative.parts
        ):
            raise ValueError("working_directory must stay inside the candidate workspace")
        if relative == PurePosixPath("."):
            return "/workspace"
        return f"/workspace/{relative.as_posix()}"

    @staticmethod
    def _parse_command_failure(stdout: str, stderr: str) -> str:
        detail = stderr or stdout
        lines = [line.strip() for line in detail.splitlines() if line.strip()]
        return lines[-1] if lines else "Container command failed without output"
