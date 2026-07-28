"""Hardened execution environment for untrusted, model-generated Python code."""

from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    """Execute generated Python in an ephemeral, resource-limited container."""

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

    def execute(self, code: str, test_suite: dict[str, Any]) -> ExecutionResult:
        self.ensure_available()
        runner_content = self._build_runner_script(code, test_suite)

        with tempfile.TemporaryDirectory(prefix="agentloop_sandbox_") as temp_dir:
            runner_path = Path(temp_dir) / "runner.py"
            runner_path.write_text(runner_content, encoding="utf-8")
            command = self._build_docker_command(Path(temp_dir).resolve())

            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    encoding="utf-8",
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    success=False,
                    message=(
                        f"运行错误：沙箱执行超时（>{self.timeout_seconds}s），"
                        "可能存在死循环或阻塞操作"
                    ),
                )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode == 0:
            return ExecutionResult(
                success=True,
                message=stdout or "通过验证",
                stdout=stdout,
                stderr=stderr,
                exit_code=completed.returncode,
            )
        return ExecutionResult(
            success=False,
            message=self._parse_stderr(stderr),
            stdout=stdout,
            stderr=stderr,
            exit_code=completed.returncode,
        )

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

    def _build_docker_command(self, temp_dir: Path) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
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

    @staticmethod
    def _build_runner_script(code: str, test_suite: dict[str, Any]) -> str:
        function_name = test_suite["function_name"]
        cases_json = json.dumps(test_suite["test_cases"], ensure_ascii=False)
        harness = textwrap.dedent(
            f"""

            import json as _agentloop_json
            import sys as _agentloop_sys

            _AGENTLOOP_CASES = _agentloop_json.loads({cases_json!r})
            _AGENTLOOP_FUNCTION = {function_name!r}

            def _agentloop_run_tests():
                target = globals().get(_AGENTLOOP_FUNCTION)
                if not callable(target):
                    print(
                        f"运行错误：代码中未定义可调用的 `{{_AGENTLOOP_FUNCTION}}` 函数",
                        file=_agentloop_sys.stderr,
                    )
                    raise SystemExit(1)

                for index, case in enumerate(_AGENTLOOP_CASES, 1):
                    args = case["args"]
                    expected = case["expected"]
                    description = case.get("description", f"用例 {{index}}")
                    try:
                        actual = target(*args)
                    except Exception as exc:
                        print(
                            f"运行错误（{{description}}）："
                            f"{{type(exc).__name__}}: {{exc}}",
                            file=_agentloop_sys.stderr,
                        )
                        raise SystemExit(1)
                    if actual != expected:
                        print(
                            f"测试失败（{{description}}）："
                            f"期望 {{expected!r}}，实际 {{actual!r}}",
                            file=_agentloop_sys.stderr,
                        )
                        raise SystemExit(1)

                print(
                    f"通过验证：`{{_AGENTLOOP_FUNCTION}}` "
                    f"全部 {{len(_AGENTLOOP_CASES)}} 组测试用例通过"
                )

            if __name__ == "__main__":
                _agentloop_run_tests()
            """
        )
        return code.rstrip() + "\n" + harness

    @staticmethod
    def _parse_stderr(stderr: str) -> str:
        lines = [line.strip() for line in stderr.splitlines() if line.strip()]
        if not lines:
            return "运行错误：容器异常退出，无错误输出"
        for line in reversed(lines):
            if line.startswith(("运行错误", "测试失败")):
                return line
        for line in reversed(lines):
            if any(word in line for word in ("Error", "Exception", "error")):
                return f"运行错误：{line}"
        return f"运行错误：{lines[-1]}"
