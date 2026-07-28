"""Agent variants that keep generated tests grounded in the task contract."""

from __future__ import annotations

from agentloop.agents import CoderAgent, CriticAgent, TesterAgent
from agentloop.models import CodingTask, LLMRequest, TestSuite
from agentloop.parsing import ModelOutputError, parse_test_suite

GROUNDED_TESTER_SYSTEM = """你是测试工程师。根据编程任务生成 JSON 测试套件。
只输出一个 JSON 对象，字段为 function_name 和 test_cases。
test_cases 每项必须包含 args、expected、description。

关键约束：
1. 测试只能验证题目明确声明的行为，不得自行增加类型检查、异常、类型转换或返回格式。
2. 如果题目没有定义特殊浮点值、无穷值、NaN 或非法输入的行为，不要测试它们。
3. expected 必须遵循 Python 的正常语义，不能为了序列化而把数字改成字符串。
4. 优先覆盖题目明确要求的正常值、边界值和代表性输入。
5. function_name 必须与题目要求完全一致。"""

GROUNDED_CRITIC_SYSTEM = """你是严格的测试评审员。检查测试套件：
1. 是否覆盖题目明确要求的正常、边界和代表性场景；
2. expected 是否符合 Python 语义；
3. 函数名是否正确；
4. 是否擅自增加题目没有声明的类型检查、异常、特殊浮点值或返回格式。

存在任何超出需求的测试时，明确指出并要求删除。
完全合格时只输出 [APPROVED]；否则只列出具体问题。"""


class GroundedTesterAgent(TesterAgent):
    """Tester that explicitly avoids inventing requirements."""

    def create_suite(self, task: CodingTask, *, critique: str = "") -> TestSuite:
        prompt = f"编程任务：\n{task.prompt}"
        if critique:
            prompt += f"\n\n评审反馈：\n{critique}\n\n请修订并重新输出完整 JSON。"

        last_error = ""
        for attempt in range(self.parse_retries + 1):
            retry_note = (
                f"\n\n上次输出错误：{last_error}\n请严格输出符合 Schema 的 JSON。"
                if attempt and last_error
                else ""
            )
            response = self.provider.generate(
                LLMRequest(
                    system_prompt=GROUNDED_TESTER_SYSTEM,
                    user_prompt=prompt + retry_note,
                    metadata={"agent": "tester", "task_id": task.task_id},
                )
            )
            try:
                suite = parse_test_suite(response.text)
                if suite.function_name not in task.prompt:
                    raise ModelOutputError(
                        f"function_name {suite.function_name!r} is not present in the task"
                    )
                return suite
            except ModelOutputError as exc:
                last_error = str(exc)
        raise ModelOutputError(
            f"Tester still returned an invalid suite after "
            f"{self.parse_retries + 1} attempts: {last_error}"
        )


class GroundedCriticAgent(CriticAgent):
    """Critic that rejects tests which expand the original contract."""

    def review(self, task: CodingTask, suite: TestSuite) -> str:
        response = self.provider.generate(
            LLMRequest(
                system_prompt=GROUNDED_CRITIC_SYSTEM,
                user_prompt=(
                    f"原始任务：\n{task.prompt}\n\n待评审测试套件：\n"
                    f"{suite.model_dump_json(indent=2)}"
                ),
                metadata={"agent": "critic", "task_id": task.task_id},
            )
        )
        return response.text.strip()


__all__ = [
    "CoderAgent",
    "GroundedCriticAgent",
    "GroundedTesterAgent",
]
