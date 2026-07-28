import subprocess
import sys

from agentloop.sandbox_v2 import DockerSandboxV2


def run_harness(code, suite, tmp_path):
    script = DockerSandboxV2._build_v2_runner_script(code, suite)
    path = tmp_path / "runner.py"
    path.write_text(script, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_v2_harness_accepts_expected_exception(tmp_path) -> None:
    result = run_harness(
        "def factorial(n):\n    if n < 0:\n        raise ValueError('negative')\n    return 1",
        {
            "function_name": "factorial",
            "test_cases": [
                {
                    "args": [-1],
                    "expected": None,
                    "expected_exception": "ValueError",
                    "description": "negative",
                }
            ],
        },
        tmp_path,
    )

    assert result.returncode == 0
    assert "Passed 1 V2 cases" in result.stdout


def test_v2_harness_rejects_wrong_exception(tmp_path) -> None:
    result = run_harness(
        "def factorial(n):\n    raise TypeError('wrong')",
        {
            "function_name": "factorial",
            "test_cases": [
                {
                    "args": [-1],
                    "expected": None,
                    "expected_exception": "ValueError",
                    "description": "negative",
                }
            ],
        },
        tmp_path,
    )

    assert result.returncode == 1
    assert "expected ValueError, got TypeError" in result.stderr
