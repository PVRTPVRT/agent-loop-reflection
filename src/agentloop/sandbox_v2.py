"""V2 Docker sandbox harness with expected-exception assertions."""

from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from agentloop.sandbox import DockerSandbox, ExecutionResult


class DockerSandboxV2(DockerSandbox):
    def execute_v2(
        self,
        code: str,
        test_suite: dict[str, Any],
    ) -> ExecutionResult:
        self.ensure_available()
        runner_content = self._build_v2_runner_script(code, test_suite)

        with tempfile.TemporaryDirectory(prefix="agentloop_sandbox_v2_") as temp_dir:
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
                    message=(f"Execution timed out after {self.timeout_seconds}s"),
                )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode == 0:
            return ExecutionResult(
                success=True,
                message=stdout or "All V2 cases passed",
                stdout=stdout,
                stderr=stderr,
                exit_code=completed.returncode,
            )
        return ExecutionResult(
            success=False,
            message=self._parse_v2_stderr(stderr),
            stdout=stdout,
            stderr=stderr,
            exit_code=completed.returncode,
        )

    @staticmethod
    def _build_v2_runner_script(
        code: str,
        test_suite: dict[str, Any],
    ) -> str:
        function_name = test_suite["function_name"]
        cases_json = json.dumps(test_suite["test_cases"], ensure_ascii=False)
        harness = textwrap.dedent(
            f"""

            import json as _agentloop_json
            import sys as _agentloop_sys

            _AGENTLOOP_CASES = _agentloop_json.loads({cases_json!r})
            _AGENTLOOP_FUNCTION = {function_name!r}

            def _agentloop_fail(message):
                print(message, file=_agentloop_sys.stderr)
                raise SystemExit(1)

            def _agentloop_run_tests():
                target = globals().get(_AGENTLOOP_FUNCTION)
                if not callable(target):
                    _agentloop_fail(
                        f"Missing callable function {{_AGENTLOOP_FUNCTION!r}}"
                    )

                for index, case in enumerate(_AGENTLOOP_CASES, 1):
                    args = case["args"]
                    expected = case["expected"]
                    expected_exception = case["expected_exception"]
                    description = case.get("description") or f"case {{index}}"
                    try:
                        actual = target(*args)
                    except Exception as exc:
                        if (
                            expected_exception is not None
                            and type(exc).__name__ == expected_exception
                        ):
                            continue
                        if expected_exception is not None:
                            _agentloop_fail(
                                f"Case {{index}} ({{description}}): expected "
                                f"{{expected_exception}}, got "
                                f"{{type(exc).__name__}}: {{exc}}"
                            )
                        _agentloop_fail(
                            f"Case {{index}} ({{description}}): unexpected "
                            f"{{type(exc).__name__}}: {{exc}}"
                        )

                    if expected_exception is not None:
                        _agentloop_fail(
                            f"Case {{index}} ({{description}}): expected "
                            f"{{expected_exception}}, but returned {{actual!r}}"
                        )
                    if actual != expected:
                        _agentloop_fail(
                            f"Case {{index}} ({{description}}): expected "
                            f"{{expected!r}}, got {{actual!r}}"
                        )

                print(
                    f"Passed {{len(_AGENTLOOP_CASES)}} V2 cases for "
                    f"{{_AGENTLOOP_FUNCTION}}"
                )

            if __name__ == "__main__":
                _agentloop_run_tests()
            """
        )
        return code.rstrip() + "\n" + harness

    @staticmethod
    def _parse_v2_stderr(stderr: str) -> str:
        lines = [line.strip() for line in stderr.splitlines() if line.strip()]
        if not lines:
            return "Container exited without an error message"
        for line in reversed(lines):
            if line.startswith(("Case ", "Missing callable")):
                return line
        return lines[-1]
