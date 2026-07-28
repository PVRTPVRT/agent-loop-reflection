from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from agentloop.sandbox import DockerSandbox, SandboxUnavailableError

TEST_SUITE = {
    "function_name": "add",
    "test_cases": [
        {
            "args": [2, 3],
            "expected": 5,
            "description": "adds two integers",
        }
    ],
}


@pytest.fixture(scope="module")
def sandbox() -> DockerSandbox:
    instance = DockerSandbox()
    if not instance.is_available():
        pytest.skip("Docker Engine is unavailable")
    return instance


def test_valid_code_runs_in_docker(sandbox: DockerSandbox) -> None:
    result = sandbox.execute("def add(a, b):\n    return a + b", TEST_SUITE)
    assert result.success, result.message
    assert "通过验证" in result.message


def test_read_only_root_blocks_writes(sandbox: DockerSandbox) -> None:
    result = sandbox.execute(
        "from pathlib import Path\n"
        "Path('/blocked.txt').write_text('no')\n"
        "def add(a, b):\n"
        "    return a + b",
        TEST_SUITE,
    )
    assert not result.success
    assert "Read-only file system" in result.message


def test_timeout_stops_infinite_loop(sandbox: DockerSandbox) -> None:
    result = sandbox.execute(
        "while True:\n    pass\ndef add(a, b):\n    return a + b",
        TEST_SUITE,
    )
    assert not result.success
    assert "执行超时" in result.message


def test_docker_command_contains_security_controls() -> None:
    command = DockerSandbox()._build_docker_command(Path("C:/sandbox"))
    command_text = " ".join(command)
    assert "--network none" in command_text
    assert "--read-only" in command
    assert "--cap-drop ALL" in command_text
    assert "--security-opt no-new-privileges" in command_text
    assert "--pids-limit 64" in command_text
    assert "--user 65534:65534" in command_text


def test_unavailable_docker_fails_closed() -> None:
    sandbox = DockerSandbox()
    unavailable = subprocess.CompletedProcess(
        args=["docker", "info"],
        returncode=1,
        stdout="",
        stderr="not running",
    )
    with patch("agentloop.sandbox.subprocess.run", return_value=unavailable):
        with pytest.raises(SandboxUnavailableError, match="安全终止"):
            sandbox.ensure_available()
