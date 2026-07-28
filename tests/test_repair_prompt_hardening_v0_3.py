from agentloop.repair_agents_v2 import (
    REPAIR_CODER_SYSTEM,
    REPAIR_CRITIC_SYSTEM,
)


def test_repair_critic_requires_code_grounded_causal_diagnosis() -> None:
    assert "逐字引用当前代码" in REPAIR_CRITIC_SYSTEM
    assert "禁止描述代码里不存在的行为" in REPAIR_CRITIC_SYSTEM
    assert "哪个状态不变量" in REPAIR_CRITIC_SYSTEM
    assert "反事实模拟失败用例" in REPAIR_CRITIC_SYSTEM
    assert "不超过 350 字" in REPAIR_CRITIC_SYSTEM


def test_repair_coder_must_reject_ungrounded_diagnosis() -> None:
    assert "Critic 诊断不是权威" in REPAIR_CODER_SYSTEM
    assert "真实控制流和失败证据" in REPAIR_CODER_SYSTEM
    assert "改变导致首个分歧的实际执行路径" in REPAIR_CODER_SYSTEM
    assert "反事实模拟第一个失败用例" in REPAIR_CODER_SYSTEM
