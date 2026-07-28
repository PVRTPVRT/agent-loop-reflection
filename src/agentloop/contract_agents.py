"""Tester and Critic grounded in an explicit public task contract."""

from __future__ import annotations

from agentloop.agents import APPROVED_MARKER
from agentloop.models import CodingTask, LLMRequest, TestSuite
from agentloop.parsing import ModelOutputError, parse_test_suite
from agentloop.public_contracts import (
    DEFAULT_CONTRACT_PATH,
    ContractRegistry,
    contract_prompt,
)

CONTRACT_TESTER_SYSTEM = """你是测试工程师。依据原始任务和公开契约生成 JSON 测试套件。
只输出符合指定 Schema 的 JSON。
公开契约是输入域、返回行为和异常规则的唯一依据。
不得测试契约未声明的输入类型、异常、类型转换、特殊值或返回格式。
不得因为没有看到具体样例而缩小契约明确声明的输入域。"""

CONTRACT_CRITIC_SYSTEM = """你是测试评审员。根据原始任务和公开契约评审测试套件。
公开契约是输入域、返回行为和异常规则的唯一依据。
契约明确包含的类型不得被视为超出需求；契约未声明的行为必须拒绝。
完全合格时，可以先简要解释，但最后一个非空行必须是 [APPROVED]。
不合格时只列出问题，且不得输出 [APPROVED]。"""


class ContractTesterAgent:
    def __init__(
        self,
        provider,
        *,
        registry: ContractRegistry | None = None,
        parse_retries: int = 2,
    ) -> None:
        self.provider = provider
        self.registry = registry or ContractRegistry.load(DEFAULT_CONTRACT_PATH)
        self.parse_retries = parse_retries

    def create_suite(self, task: CodingTask, *, critique: str = "") -> TestSuite:
        contract = self.registry.require(task.task_id)
        prompt = f"原始任务：\n{task.prompt}\n\n公开契约：\n{contract_prompt(contract)}"
        if critique:
            prompt += f"\n\n评审反馈：\n{critique}\n\n请修订并重新输出完整 JSON。"

        last_error = ""
        for attempt in range(self.parse_retries + 1):
            retry_note = (
                f"\n\n上次输出错误：{last_error}\n请重新输出合法 JSON。"
                if attempt and last_error
                else ""
            )
            response = self.provider.generate(
                LLMRequest(
                    system_prompt=CONTRACT_TESTER_SYSTEM,
                    user_prompt=prompt + retry_note,
                    metadata={"agent": "tester", "task_id": task.task_id},
                )
            )
            try:
                suite = parse_test_suite(response.text)
                if suite.function_name != contract.function_name:
                    raise ModelOutputError(
                        f"Expected function_name {contract.function_name!r}, "
                        f"got {suite.function_name!r}"
                    )
                return suite
            except ModelOutputError as exc:
                last_error = str(exc)
        raise ModelOutputError(
            f"Tester still returned an invalid suite after "
            f"{self.parse_retries + 1} attempts: {last_error}"
        )


class ContractCriticAgent:
    def __init__(
        self,
        provider,
        *,
        registry: ContractRegistry | None = None,
    ) -> None:
        self.provider = provider
        self.registry = registry or ContractRegistry.load(DEFAULT_CONTRACT_PATH)

    def review(self, task: CodingTask, suite: TestSuite) -> str:
        contract = self.registry.require(task.task_id)
        response = self.provider.generate(
            LLMRequest(
                system_prompt=CONTRACT_CRITIC_SYSTEM,
                user_prompt=(
                    f"原始任务：\n{task.prompt}\n\n公开契约：\n"
                    f"{contract_prompt(contract)}\n\n待评审测试套件：\n"
                    f"{suite.model_dump_json(indent=2)}"
                ),
                metadata={"agent": "critic", "task_id": task.task_id},
            )
        )
        return response.text.strip()

    @staticmethod
    def is_approved(verdict: str) -> bool:
        lines = [line.strip() for line in verdict.splitlines() if line.strip()]
        return bool(lines and lines[-1] == APPROVED_MARKER)
