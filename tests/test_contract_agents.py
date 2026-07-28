from agentloop.contract_agents import ContractCriticAgent, ContractTesterAgent
from agentloop.llm import FakeLLMProvider
from agentloop.models import CodingTask, TestCase, TestSuite


def test_tester_receives_public_float_domain() -> None:
    provider = FakeLLMProvider(
        [
            """{"function_name":"add","test_cases":[
            {"args":[1.5,2.5],"expected":4.0,"description":"floats"}]}"""
        ]
    )
    agent = ContractTesterAgent(provider)

    suite = agent.create_suite(
        CodingTask(
            task_id="add-001",
            prompt="实现 Python 函数 add(a, b)，返回两个数字之和。",
        )
    )

    assert suite.test_cases[0].expected == 4.0
    assert "integer or finite float" in provider.requests[0].user_prompt


def test_critic_receives_same_public_contract() -> None:
    provider = FakeLLMProvider(["解释\n[APPROVED]"])
    suite = TestSuite(
        function_name="add",
        test_cases=[TestCase(args=[1.5, 2.5], expected=4.0, description="floats")],
    )
    agent = ContractCriticAgent(provider)

    verdict = agent.review(
        CodingTask(task_id="add-001", prompt="实现 add(a, b)"),
        suite,
    )

    assert agent.is_approved(verdict)
    assert "integer or finite float" in provider.requests[0].user_prompt
