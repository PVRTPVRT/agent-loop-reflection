from pathlib import Path

import pytest

from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2
from agentloop.sandbox import DEFAULT_SANDBOX_IMAGE


def test_default_sandbox_image_is_pinned_by_digest() -> None:
    assert ManagedDockerSandboxV2().image == DEFAULT_SANDBOX_IMAGE
    assert "@sha256:" in DEFAULT_SANDBOX_IMAGE


def test_create_command_preserves_tokens_and_security_controls(tmp_path) -> None:
    command = ManagedDockerSandboxV2()._build_create_command(
        "agentloop-test",
        tmp_path,
        command=("python", "-B", "-m", "unittest", "-q"),
        container_workdir="/workspace/tests",
        read_only=True,
    )

    assert command[-5:] == ["python", "-B", "-m", "unittest", "-q"]
    assert command[command.index("--network") + 1] == "none"
    assert "--read-only" in command
    assert "--cap-drop" in command
    assert "ALL" in command
    assert "--security-opt" in command
    assert "no-new-privileges" in command
    assert command[command.index("--workdir") + 1] == "/workspace/tests"
    assert command[command.index("--volume") + 1].endswith(":/workspace:ro")


@pytest.mark.parametrize(
    "working_directory",
    ["", " ", "/tmp", r"C:\temp", "C:temp", "../tests"],
)
def test_container_workdir_rejects_workspace_escape(working_directory: str) -> None:
    with pytest.raises(ValueError):
        ManagedDockerSandboxV2._container_workdir(working_directory)


def test_execute_workspace_rejects_missing_workspace_before_docker(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="existing directory"):
        ManagedDockerSandboxV2().execute_workspace(
            tmp_path / "missing",
            command=("python", "-V"),
            working_directory=".",
            timeout_seconds=10,
            read_only=True,
        )


@pytest.mark.parametrize("timeout_seconds", [0, 601])
def test_execute_workspace_rejects_unbounded_timeout(
    tmp_path: Path,
    timeout_seconds: int,
) -> None:
    with pytest.raises(ValueError, match="between 1 and 600"):
        ManagedDockerSandboxV2().execute_workspace(
            tmp_path,
            command=("python", "-V"),
            working_directory=".",
            timeout_seconds=timeout_seconds,
            read_only=True,
        )
