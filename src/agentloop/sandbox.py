"""Shared Docker runtime configuration for managed verification."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


class SandboxUnavailableError(RuntimeError):
    """Raised when the secure Docker execution boundary is unavailable."""


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    success: bool
    message: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None


class DockerSandbox:
    """Prepare the Docker runtime used by managed sandbox implementations."""

    def __init__(
        self,
        *,
        image: str = "python:3.12-slim",
        timeout_seconds: int = 5,
        pull_timeout_seconds: int = 120,
        memory_limit: str = "128m",
        cpu_limit: str = "0.5",
        pids_limit: int = 64,
    ) -> None:
        self.image = image
        self.timeout_seconds = timeout_seconds
        self.pull_timeout_seconds = pull_timeout_seconds
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.pids_limit = pids_limit

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0

    def ensure_available(self) -> None:
        if not self.is_available():
            raise SandboxUnavailableError(
                "Docker Engine 不可用；为避免在宿主机执行不可信代码，任务已安全终止。"
            )
        self._ensure_image()

    def _ensure_image(self) -> None:
        try:
            inspected = subprocess.run(
                ["docker", "image", "inspect", self.image],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if inspected.returncode == 0:
                return
            pulled = subprocess.run(
                ["docker", "pull", self.image],
                capture_output=True,
                text=True,
                timeout=self.pull_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SandboxUnavailableError(f"Docker 镜像准备超时：{self.image}") from exc
        except (FileNotFoundError, OSError) as exc:
            raise SandboxUnavailableError("无法调用 Docker CLI") from exc

        if pulled.returncode != 0:
            error = pulled.stderr.strip() or "未知错误"
            raise SandboxUnavailableError(f"Docker 镜像拉取失败：{error}")
