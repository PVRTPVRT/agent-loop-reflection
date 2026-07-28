"""V2 agents with contract validation before debate or code generation."""

from __future__ import annotations

import json

from pydantic import ValidationError

from agentloop.agents import APPROVED_MARKER
from agentloop.contracts_v2 import (
    DEFAULT_V2_CONTRACT_PATH,
    ContractRegistryV2,
    render_contract,
)
from agentloop.evaluation_v2_models import EvaluationSuite, EvaluationTask
from agentloop.models import LLMRequest
from agentloop.parsing import ModelOutputError, extract_json_object
from agentloop.suite_validation import SuiteContractError, validate_suite

V2_TESTER_SYSTEM = """你是测试工程师。根据原始任务和公开契约生成 V2 JSON 测试套件。
每个用例必须包含 args、expected、expected_exception、description。
普通返回值：expected 填正确值，expected_exception 填 null。
预期异常：expected 填 null，expected_exception 填异常类名，例如 "ValueError"。
只测试公开契约允许的输入，并严格遵守 Python 语义。
不要使用占位符、伪造的大数、不可判定的 expected 或契约外输入。
只输出 JSON。"""

V2_CRITIC_SYSTEM = """你是测试评审员。测试套件已经通过机器契约与可信 Oracle 校验。
请评审覆盖质量，禁止要求契约外输入或未声明行为。
完全合格时，最后一个非空行输出 [APPROVED]。
不合格时只给出具体、契约内的改进意见，不输出 [APPROVED]。"""

V2_CODER_SYSTEM = """你是 Python 程序员。根据原始任务、公开契约和已校验测试生成代码。
expected_exception 表示对应输入必须抛出该异常。
只输出完整可运行的 Python 代码，不要解释。"""


class EvaluationTesterAgent:
    def __init__(
        self,
        provider,
        *,
        registry: ContractRegistryV2 | None = None,
        retries: int = 2,
    ) -> None:
        self.provider = provider
        self.registry = registry or ContractRegistryV2.load(DEFAULT_V2_CONTRACT_PATH)
        self.retries = retries

    def create_suite(
        self,
        task: EvaluationTask,
        *,
        critique: str = "",
    ) -> EvaluationSuite:
        contract = self.registry.require(task.task_id)
        feedback = critique
        for _ in range(self.retries + 1):
            response = self.provider.generate(
                LLMRequest(
                    system_prompt=V2_TESTER_SYSTEM,
                    user_prompt=(
                        f"原始任务：\n{task.prompt}\n\n公开契约：\n"
                        f"{render_contract(contract)}"
                        + (f"\n\n修订反馈：\n{feedback}" if feedback else "")
                    ),
                    metadata={"agent": "tester", "task_id": task.task_id},
                )
            )
            try:
                suite = EvaluationSuite.model_validate(extract_json_object(response.text))
                return validate_suite(suite, contract)
            except (
                ModelOutputError,
                ValidationError,
                SuiteContractError,
            ) as exc:
                feedback = f"机器校验失败：{exc}\n请只修正这些问题并重新输出完整 JSON。"
        raise ModelOutputError(
            f"Tester failed V2 contract validation after {self.retries + 1} attempts: {feedback}"
        )


class EvaluationCriticAgent:
    def __init__(
        self,
        provider,
        *,
        registry: ContractRegistryV2 | None = None,
    ) -> None:
        self.provider = provider
        self.registry = registry or ContractRegistryV2.load(DEFAULT_V2_CONTRACT_PATH)

    def review(
        self,
        task: EvaluationTask,
        suite: EvaluationSuite,
    ) -> str:
        contract = self.registry.require(task.task_id)
        response = self.provider.generate(
            LLMRequest(
                system_prompt=V2_CRITIC_SYSTEM,
                user_prompt=(
                    f"原始任务：\n{task.prompt}\n\n公开契约：\n"
                    f"{render_contract(contract)}\n\n已通过机器校验的测试：\n"
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


class EvaluationCoderAgent:
    def __init__(
        self,
        provider,
        *,
        registry: ContractRegistryV2 | None = None,
    ) -> None:
        self.provider = provider
        self.registry = registry or ContractRegistryV2.load(DEFAULT_V2_CONTRACT_PATH)

    def generate_code(
        self,
        task: EvaluationTask,
        suite: EvaluationSuite,
        *,
        feedback: str = "",
    ) -> str:
        contract = self.registry.require(task.task_id)
        prompt = (
            f"原始任务：\n{task.prompt}\n\n公开契约：\n"
            f"{render_contract(contract)}\n\n已校验测试：\n"
            f"{json.dumps(suite.model_dump(mode='json'), ensure_ascii=False)}"
        )
        if feedback:
            prompt += f"\n\n上一轮验证失败：\n{feedback}\n请修复代码。"
        response = self.provider.generate(
            LLMRequest(
                system_prompt=V2_CODER_SYSTEM,
                user_prompt=prompt,
                metadata={"agent": "coder", "task_id": task.task_id},
            )
        )
        from agentloop.parsing import extract_python_code

        return extract_python_code(response.text)
