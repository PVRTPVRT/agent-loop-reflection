import subprocess

import pytest

from agentloop.evaluation_v2_models import EvaluationCase, EvaluationSuite
from agentloop.evaluation_verifier import EvaluationCodeVerifier
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2


def agentloop_container_ids() -> list[str]:
    result = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "name=agentloop-"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_managed_sandbox_removes_container_after_success() -> None:
    sandbox = ManagedDockerSandboxV2()
    if not sandbox.is_available():
        pytest.skip("Docker Engine is unavailable")
    before = set(agentloop_container_ids())
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
    assert set(agentloop_container_ids()) == before


def test_managed_sandbox_removes_container_after_timeout() -> None:
    sandbox = ManagedDockerSandboxV2(timeout_seconds=1)
    if not sandbox.is_available():
        pytest.skip("Docker Engine is unavailable")
    before = set(agentloop_container_ids())
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
    assert set(agentloop_container_ids()) == before
