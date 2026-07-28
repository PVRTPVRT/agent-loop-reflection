import pytest

from agentloop.evaluation_v2_models import EvaluationCase, EvaluationSuite
from agentloop.evaluation_verifier import EvaluationCodeVerifier
from agentloop.sandbox_v2 import DockerSandboxV2


def test_docker_accepts_required_value_error() -> None:
    sandbox = DockerSandboxV2()
    if not sandbox.is_available():
        pytest.skip("Docker Engine is unavailable")

    suite = EvaluationSuite(
        function_name="factorial",
        test_cases=[
            EvaluationCase(
                args=[-1],
                expected=None,
                expected_exception="ValueError",
                description="negative",
            )
        ],
    )
    code = """def factorial(n):
    if n < 0:
        raise ValueError("negative")
    return 1
"""

    result = EvaluationCodeVerifier(sandbox=sandbox).verify(code, suite)

    assert result.success is True
    assert "Passed 1 V2 cases" in result.message
