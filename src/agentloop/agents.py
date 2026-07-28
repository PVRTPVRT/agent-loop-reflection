"""Agent roles built on the provider-neutral LLM interface."""

from __future__ import annotations

import json

from agentloop.llm import LLMProvider
from agentloop.models import CodingTask, LLMRequest, TestSuite
from agentloop.parsing import ModelOutputError, extract_python_code, parse_test_suite

APPROVED_MARKER = "[APPROVED]"

TESTER_SYSTEM = """你是测试工程师。根据编程任务生成 JSON 测试套件。
只输出一个 JSON 对象，字段为 function_name 和 test_cases。
test_cases 每项包含 args、expected、description。覆盖正常、边界和复杂场景。"""

CRITIC_SYSTEM = """你是严格的测试评审员。检查测试套件的边界覆盖、expected 正确性、
代表性和函数签名。完全合格时只输出 [APPROVED]；否则只列出具体问题。"""

CODER_SYSTEM = """你是 Python 程序员。根据任务、测试目标和验证反馈生成完整代码。
只输出 Python 代码或一个 python Markdown 代码块，不要解释。"""


class TesterAgent:
    def __init__(self, provider: LLMProvider, *, parse_retries: int = 2) -> None:
        self.provider = provider
        self.parse_retries = parse_retries

    def create_suite(self, task: CodingTask, *, critique: str = "") -> TestSuite:
        prompt = f"编程任务：\n{task.prompt}"
        if critique:
            prompt += f"\n\n评审反馈：\n{critique}\n\n请修订并重新输出完整 JSON。"

        last_error = ""
        for attempt in range(self.parse_retries + 1):
            retry_note = (
                f"\n\n上次输出错误：{last_error}\n请严格输出合法 JSON。"
                if attempt and last_error
                else ""
            )
            response = self.provider.generate(
                LLMRequest(
                    system_prompt=TESTER_SYSTEM,
                    user_prompt=prompt + retry_note,
                    metadata={"agent": "tester", "task_id": task.task_id},
                )
            )
            try:
                return parse_test_suite(response.text)
            except ModelOutputError as exc:
                last_error = str(exc)
        raise ModelOutputError(
            f"Tester 在 {self.parse_retries + 1} 次尝试后仍未返回有效测试套件：{last_error}"
        )


class CriticAgent:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def review(self, task: CodingTask, suite: TestSuite) -> str:
        response = self.provider.generate(
            LLMRequest(
                system_prompt=CRITIC_SYSTEM,
                user_prompt=(
                    f"任务：\n{task.prompt}\n\n测试套件：\n{suite.model_dump_json(indent=2)}"
                ),
                metadata={"agent": "critic", "task_id": task.task_id},
            )
        )
        return response.text.strip()

    @staticmethod
    def is_approved(verdict: str) -> bool:
        return verdict.strip() == APPROVED_MARKER


class CoderAgent:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def generate_code(
        self,
        task: CodingTask,
        suite: TestSuite,
        *,
        feedback: str = "",
    ) -> str:
        test_contract = json.dumps(
            [case.model_dump() for case in suite.test_cases],
            ensure_ascii=False,
        )
        prompt = (
            f"任务：\n{task.prompt}\n\n目标函数：{suite.function_name}\n验收用例：{test_contract}"
        )
        if feedback:
            prompt += f"\n\n上一轮验证失败：\n{feedback}\n请修复代码。"
        response = self.provider.generate(
            LLMRequest(
                system_prompt=CODER_SYSTEM,
                user_prompt=prompt,
                metadata={"agent": "coder", "task_id": task.task_id},
            )
        )
        return extract_python_code(response.text)
