from pathlib import Path

import pytest

from agentloop.evaluation_v2_models import (
    EvaluationCase,
    EvaluationDataset,
    EvaluationSuite,
)
from agentloop.evaluation_verifier import EvaluationCodeVerifier
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2


def test_docker_accepts_required_value_error() -> None:
    sandbox = ManagedDockerSandboxV2()
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


def test_docker_accepts_frame_decoder_reference() -> None:
    sandbox = ManagedDockerSandboxV2()
    if not sandbox.is_available():
        pytest.skip("Docker Engine is unavailable")

    dataset = EvaluationDataset.load(
        "benchmarks/datasets/coding-v3-frame-decoder-pilot.json"
    )
    code = Path("benchmarks/fixtures/frame-decoder-reference.py").read_text(
        encoding="utf-8"
    )

    result = EvaluationCodeVerifier(sandbox=sandbox).verify(
        code,
        dataset.tasks[0].evaluation_suite,
    )

    assert result.success is True
    assert "Passed 9 V2 cases" in result.message


def test_docker_accepts_idempotent_ledger_reference() -> None:
    sandbox = ManagedDockerSandboxV2()
    if not sandbox.is_available():
        pytest.skip("Docker Engine is unavailable")

    dataset = EvaluationDataset.load(
        "benchmarks/datasets/coding-v3-idempotent-ledger-pilot.json"
    )
    code = Path("benchmarks/fixtures/idempotent-ledger-reference.py").read_text(
        encoding="utf-8"
    )

    result = EvaluationCodeVerifier(sandbox=sandbox).verify(
        code,
        dataset.tasks[0].evaluation_suite,
    )

    assert result.success is True
    assert "Passed 8 V2 cases" in result.message
