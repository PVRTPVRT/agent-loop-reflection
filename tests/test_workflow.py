from agentloop.agents import CoderAgent, CriticAgent, TesterAgent
from agentloop.llm import FakeLLMProvider
from agentloop.models import CodingTask, TestSuite
from agentloop.verifier import VerificationResult
from agentloop.workflow import ReflectionWorkflow


class SequenceVerifier:
    def __init__(self, results: list[VerificationResult]) -> None:
        self.results = iter(results)
        self.calls: list[tuple[str, TestSuite]] = []

    def verify(self, code: str, suite: TestSuite) -> VerificationResult:
        self.calls.append((code, suite))
        return next(self.results)


def test_reflection_workflow_repairs_failed_code_offline() -> None:
    provider = FakeLLMProvider(
        [
            """{
              "function_name": "add",
              "test_cases": [
                {"args": [1, 2], "expected": 3, "description": "normal"},
                {"args": [0, 0], "expected": 0, "description": "zero"}
              ]
            }""",
            "[APPROVED]",
            "```python\ndef add(a, b):\n    return a - b\n```",
            "```python\ndef add(a, b):\n    return a + b\n```",
        ]
    )
    verifier = SequenceVerifier(
        [
            VerificationResult(success=False, message="测试失败：期望 3，实际 -1"),
            VerificationResult(success=True, message="通过验证"),
        ]
    )
    workflow = ReflectionWorkflow(
        tester=TesterAgent(provider),
        critic=CriticAgent(provider),
        coder=CoderAgent(provider),
        verifier=verifier,
    )

    result = workflow.run(CodingTask(task_id="add-001", prompt="实现 add(a, b)"))

    assert result.success
    assert result.debate_rounds == 1
    assert result.coding_rounds == 2
    assert result.code == "def add(a, b):\n    return a + b"
    assert [event.event_type for event in result.events] == [
        "suite_created",
        "suite_reviewed",
        "code_generated",
        "code_verified",
        "code_generated",
        "code_verified",
    ]
    assert "上一轮验证失败" in provider.requests[-1].user_prompt


def test_workflow_revises_suite_after_critique() -> None:
    provider = FakeLLMProvider(
        [
            """{"function_name":"identity","test_cases":[
              {"args":[1],"expected":1,"description":"normal"}]}""",
            "缺少空字符串边界场景",
            """{"function_name":"identity","test_cases":[
              {"args":[1],"expected":1,"description":"normal"},
              {"args":[""],"expected":"","description":"empty"}]}""",
            "[APPROVED]",
            "def identity(value):\n    return value",
        ]
    )
    verifier = SequenceVerifier([VerificationResult(success=True, message="通过验证")])
    workflow = ReflectionWorkflow(
        tester=TesterAgent(provider),
        critic=CriticAgent(provider),
        coder=CoderAgent(provider),
        verifier=verifier,
    )

    result = workflow.run(CodingTask(task_id="identity-001", prompt="实现 identity(value)"))

    assert result.success
    assert result.debate_rounds == 2
    assert len(result.test_suite.test_cases) == 2
    assert any(event.event_type == "suite_revised" for event in result.events)
