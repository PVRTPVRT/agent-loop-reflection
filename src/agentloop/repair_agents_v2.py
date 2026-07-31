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
先逐字引用当前代码中导致首个分歧的“故障语句”；任何声称发生的调用、分支或状态
变化都必须能在当前候选中找到，禁止描述代码里不存在的行为。
从 actual 与 expected 的首个差异反向追踪，说明哪个状态不变量被该语句破坏。
重点检查边界条件、状态更新顺序、数据结构遍历与排序假设；不得用猜测替代追踪。
提出最小修复后，必须反事实模拟失败用例，确认它会改变致错路径并得到 expected。
如果最新验证否定了上一轮思路，必须放弃旧诊断并根据当前候选重新定位。
不要重新设计测试，不要假设隐藏测试内容，不要输出完整代码。
严格按“故障语句、失效不变量、证据、最小修复、反事实验证”输出，总计不超过 350 字。"""

REPAIR_CODER_SYSTEM = """你是 Python 代码修复工程师。
基于当前失败候选、公开契约、已知失败证据和 Critic 诊断进行最小修复。
Critic 诊断不是权威；如果它声称的调用或分支不在当前代码中，必须忽略该诊断，
并根据当前代码的真实控制流和失败证据重新定位。
修复必须直接解释 expected 与 actual 的差异，并改变导致首个分歧的实际执行路径；
不要只删除无关的冗余检查，也不要在验证结果未变化时返回语义相同的候选。
输出前反事实模拟第一个失败用例，确认修改后的状态和 expected 一致。
保留候选中已经正确的行为，不要编写或修改测试。
只输出完整可运行的 Python 代码，不要解释。"""


def render_repair_history(context: RepairContext) -> str:
    if not context.attempts:
        return "Repair history: no earlier failed repair attempts."
    lines = [
        "Repair history (do not repeat a hypothesis or return to a known failed state):"
    ]
    for attempt in context.attempts:
        diagnosis = " ".join(attempt.diagnosis.split())
        if len(diagnosis) > 600:
            diagnosis = diagnosis[:597] + "..."
        lines.append(
            f"- round {attempt.round_number}: verifier={attempt.verification_message!r}; "
            f"diagnosis={diagnosis!r}"
        )
    return "\n".join(lines)


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
                    f"\n\n{render_repair_history(context)}"
                ),
                metadata={
                    "agent": "critic",
                    "phase": "repair",
                    "task_id": task.task_id,
                    "repair_round": str(
                        context.attempts[-1].round_number + 1
                        if context.attempts
                        else 1
                    ),
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
            f"\n\n{render_repair_history(context)}"
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
                    "repair_round": str(
                        context.attempts[-1].round_number + 1
                        if context.attempts
                        else 1
                    ),
                },
            )
        )
        return extract_python_code(response.text)
