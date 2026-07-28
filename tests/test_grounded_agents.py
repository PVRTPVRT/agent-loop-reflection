from agentloop.grounded_agents import (
    GROUNDED_CRITIC_SYSTEM,
    GROUNDED_TESTER_SYSTEM,
    GroundedCriticAgent,
    GroundedTesterAgent,
)
from agentloop.llm import FakeLLMProvider
from agentloop.models import CodingTask, TestCase, TestSuite


def test_grounded_tester_prompt_forbids_requirement_expansion() -> None:
    provider = FakeLLMProvider(
        [
            """{"function_name":"add","test_cases":[
            {"args":[1,2],"expected":3,"description":"normal"}]}"""
        ]
    )

    suite = GroundedTesterAgent(provider).create_suite(
        CodingTask(task_id="add-001", prompt="实现 add(a, b)，返回两个数字之和。")
    )

    assert suite.function_name == "add"
    assert "不得自行增加" in GROUNDED_TESTER_SYSTEM
    assert provider.requests[0].metadata["agent"] == "tester"


def test_grounded_critic_checks_scope_expansion() -> None:
    provider = FakeLLMProvider(["[APPROVED]"])
    suite = TestSuite(
        function_name="add",
        test_cases=[TestCase(args=[1, 2], expected=3, description="normal")],
    )

    verdict = GroundedCriticAgent(provider).review(
        CodingTask(task_id="add-001", prompt="实现 add(a, b)"),
        suite,
    )

    assert verdict == "[APPROVED]"
    assert "擅自增加" in GROUNDED_CRITIC_SYSTEM
