import re
import subprocess

import pytest

from agentloop.evaluation_v2_models import EvaluationCase, EvaluationSuite
from agentloop.evaluation_verifier import EvaluationCodeVerifier
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2


def managed_execution_container_names() -> list[str]:
    result = subprocess.run(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            "name=agentloop-",
            "--format",
            "{{.Names}}",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return [
        name
        for name in result.stdout.splitlines()
        if re.fullmatch(r"agentloop-[0-9a-f]{12}", name)
    ]


def test_managed_sandbox_removes_container_after_success() -> None:
    sandbox = ManagedDockerSandboxV2()
    if not sandbox.is_available():
        pytest.skip("Docker Engine is unavailable")
    assert managed_execution_container_names() == []
    suite = EvaluationSuite(
        function_name="identity",
        test_cases=[
            EvaluationCase(
                args=[1],
                expected=1,
                expected_exception=None,
                description="one",
            )
        ],
    )

    result = EvaluationCodeVerifier(sandbox=sandbox).verify(
        "def identity(value):\n    return value",
        suite,
    )

    assert result.success is True
    assert managed_execution_container_names() == []


def test_managed_sandbox_removes_container_after_timeout() -> None:
    sandbox = ManagedDockerSandboxV2(timeout_seconds=1)
    if not sandbox.is_available():
        pytest.skip("Docker Engine is unavailable")
    assert managed_execution_container_names() == []
    suite = EvaluationSuite(
        function_name="forever",
        test_cases=[
            EvaluationCase(
                args=[],
                expected=None,
                expected_exception=None,
                description="timeout",
            )
        ],
    )

    result = EvaluationCodeVerifier(sandbox=sandbox).verify(
        "def forever():\n    while True:\n        pass",
        suite,
    )

    assert result.success is False
    assert "timed out" in result.message
    assert managed_execution_container_names() == []
