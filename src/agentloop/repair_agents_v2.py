"""Evidence-aware Critic and Coder roles used only after a failed Direct route."""

from __future__ import annotations

import json

from agentloop.contracts_v2 import render_contract
from agentloop.evaluation_agents import EvaluationCoderAgent, EvaluationCriticAgent
from agentloop.evaluation_v2_models import EvaluationTask
from agentloop.models import LLMRequest
from agentloop.parsing import extract_python_code
from agentloop.repair_v2 import RepairContext

REPAIR_CRITIC_SYSTEM = """你是代码故障诊断员。
只根据原始任务、公开契约、当前失败代码和路由验证证据定位根因。
逐事件或逐步骤模拟第一个失败用例，找出 expected 与 actual 首次分歧前的状态。
重点检查边界条件、状态更新顺序、数据结构遍历与排序假设；不得用猜测替代追踪。
如果最新验证否定了上一轮思路，必须放弃旧诊断并根据当前候选重新定位。
不要重新设计测试，不要假设隐藏测试内容，不要输出完整代码。
按根因、证据、最小修复三部分输出简洁、可执行的诊断。"""

REPAIR_CODER_SYSTEM = """你是 Python 代码修复工程师。
基于当前失败候选、公开契约、已知失败证据和 Critic 诊断进行最小修复。
修复必须直接解释 expected 与 actual 的差异；不要只删除无关的冗余检查。
保留候选中已经正确的行为，不要编写或修改测试。
只输出完整可运行的 Python 代码，不要解释。"""


class RepairEvaluationCriticAgent(EvaluationCriticAgent):
    def diagnose_repair(
        self,
        task: EvaluationTask,
        context: RepairContext,
    ) -> str:
        contract = self.registry.require(task.task_id)
        response = self.provider.generate(
            LLMRequest(
                system_prompt=REPAIR_CRITIC_SYSTEM,
                user_prompt=(
                    f"原始任务：\n{task.prompt}\n\n公开契约：\n"
                    f"{render_contract(contract)}\n\n当前失败候选：\n"
                    f"```python\n{context.failed_code}\n```\n\n"
                    f"路由验证失败：\n{context.verification_message}\n\n"
                    "公开路由测试：\n"
                    f"{context.routing_suite.model_dump_json(indent=2)}"
                ),
                metadata={
                    "agent": "critic",
                    "phase": "repair",
                    "task_id": task.task_id,
                },
            )
        )
        return response.text.strip()


class RepairEvaluationCoderAgent(EvaluationCoderAgent):
    def repair_code(
        self,
        task: EvaluationTask,
        context: RepairContext,
        *,
        diagnosis: str,
        feedback: str = "",
    ) -> str:
        contract = self.registry.require(task.task_id)
        prompt = (
            f"原始任务：\n{task.prompt}\n\n公开契约：\n"
            f"{render_contract(contract)}\n\n当前失败候选：\n"
            f"```python\n{context.failed_code}\n```\n\n"
            f"路由验证失败：\n{context.verification_message}\n\n"
            f"Critic 诊断：\n{diagnosis}\n\n"
            "用于修复验收的公开路由测试：\n"
            f"{json.dumps(context.routing_suite.model_dump(mode='json'), ensure_ascii=False)}"
        )
        if feedback:
            prompt += f"\n\n上一轮修复仍失败：\n{feedback}\n请继续修复。"
        response = self.provider.generate(
            LLMRequest(
                system_prompt=REPAIR_CODER_SYSTEM,
                user_prompt=prompt,
                metadata={
                    "agent": "coder",
                    "phase": "repair",
                    "task_id": task.task_id,
                },
            )
        )
        return extract_python_code(response.text)
