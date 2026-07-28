from agentloop import v2


def test_v2_public_api_exports_only_managed_sandbox() -> None:
    assert v2.ManagedDockerSandboxV2.__name__ == "ManagedDockerSandboxV2"
    assert "DockerSandbox" not in v2.__all__


def test_v2_public_models_are_available() -> None:
    case = v2.EvaluationCase(
        args=[-1],
        expected=None,
        expected_exception="ValueError",
        description="negative",
    )

    assert case.expected_exception == "ValueError"
