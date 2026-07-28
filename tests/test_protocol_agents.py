from agentloop.protocol_agents import ProtocolCriticAgent


def test_accepts_explanation_followed_by_approval_marker() -> None:
    verdict = "测试符合原始需求。\n\n[APPROVED]"

    assert ProtocolCriticAgent.is_approved(verdict) is True


def test_accepts_marker_by_itself() -> None:
    assert ProtocolCriticAgent.is_approved("[APPROVED]") is True


def test_rejects_marker_inside_rejection_explanation() -> None:
    verdict = "不要输出 [APPROVED]，因为测试超出了需求。"

    assert ProtocolCriticAgent.is_approved(verdict) is False


def test_rejects_text_after_marker() -> None:
    verdict = "[APPROVED]\n但仍然缺少一个边界用例。"

    assert ProtocolCriticAgent.is_approved(verdict) is False
