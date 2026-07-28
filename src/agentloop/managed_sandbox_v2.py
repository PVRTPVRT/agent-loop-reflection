"""Managed Docker lifecycle that guarantees container cleanup."""

from __future__ import annotations

import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from agentloop.sandbox import ExecutionResult, SandboxUnavailableError
from agentloop.sandbox_v2 import DockerSandboxV2


class ManagedDockerSandboxV2(DockerSandboxV2):
    """Create named containers and remove them in a finally block."""

    def __init__(self, *, timeout_seconds: int = 15, **kwargs) -> None:
        super().__init__(timeout_seconds=timeout_seconds, **kwargs)

    def execute_v2(
        self,
        code: str,
        test_suite: dict[str, Any],
    ) -> ExecutionResult:
        self.ensure_available()
        name = f"agentloop-{uuid.uuid4().hex[:12]}"
        runner_content = self._build_v2_runner_script(code, test_suite)

        try:
            with tempfile.TemporaryDirectory(prefix="agentloop_managed_v2_") as temp_dir:
                self._write_runner_script(Path(temp_dir), runner_content)
                create = subprocess.run(
                    self._build_create_command(name, Path(temp_dir).resolve()),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding="utf-8",
                    check=False,
                )
                if create.returncode != 0:
                    raise SandboxUnavailableError(
                        f"Docker create failed: {create.stderr.strip() or create.stdout.strip()}"
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
                    raise SandboxUnavailableError(f"Docker start failed: {start.stderr.strip()}")

                try:
                    waited = subprocess.run(
                        ["docker", "wait", name],
                        capture_output=True,
                        text=True,
                        timeout=self.timeout_seconds,
                        encoding="utf-8",
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    return ExecutionResult(
                        success=False,
                        message=(f"Execution timed out after {self.timeout_seconds}s"),
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
                        message=stdout or "All V2 cases passed",
                        stdout=stdout,
                        stderr=stderr,
                        exit_code=exit_code,
                    )
                return ExecutionResult(
                    success=False,
                    message=self._parse_v2_stderr(stderr),
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
        temp_dir: Path,
    ) -> list[str]:
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
            "--volume",
            f"{temp_dir}:/app:ro",
            self.image,
            "python",
            "-B",
            "/app/runner.py",
        ]
