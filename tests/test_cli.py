from agentloop.cli import main
from agentloop.models import TestCase, TestSuite
from agentloop.workflow import WorkflowResult


class StubWorkflow:
    def __init__(self, result: WorkflowResult) -> None:
        self.result = result
        self.tasks = []

    def run(self, task):
        self.tasks.append(task)
        return self.result


def make_result(*, success: bool = True) -> WorkflowResult:
    return WorkflowResult(
        task_id="cli-test",
        success=success,
        code="def add(a, b):\n    return a + b",
        test_suite=TestSuite(
            function_name="add",
            test_cases=[TestCase(args=[1, 2], expected=3)],
        ),
        debate_rounds=1,
        coding_rounds=1,
        final_message="通过验证" if success else "测试失败",
        events=(),
    )


def test_cli_runs_workflow_without_real_api(monkeypatch, capsys) -> None:
    workflow = StubWorkflow(make_result())
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("agentloop.cli.build_workflow", lambda settings: workflow)

    exit_code = main(["实现 add(a, b)", "--task-id", "cli-test"])

    output = capsys.readouterr()
    assert exit_code == 0
    assert "[成功] task_id=cli-test" in output.out
    assert workflow.tasks[0].prompt == "实现 add(a, b)"


def test_cli_json_output(monkeypatch, capsys) -> None:
    workflow = StubWorkflow(make_result())
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("agentloop.cli.build_workflow", lambda settings: workflow)

    exit_code = main(["实现 add(a, b)", "--json"])

    output = capsys.readouterr()
    assert exit_code == 0
    assert '"success": true' in output.out
    assert '"function_name": "add"' in output.out


def test_cli_reports_missing_api_key(monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main(["实现 add(a, b)"])

    output = capsys.readouterr()
    assert exit_code == 2
    assert "配置错误" in output.err
