from agentloop.lean_evaluation import LeanNormalizedEvaluationWorkflow


def test_lean_workflow_forces_one_critic_round() -> None:
    workflow = LeanNormalizedEvaluationWorkflow(
        tester=object(),
        critic=object(),
        coder=object(),
        verifier=object(),
        max_debate_rounds=9,
        max_coding_rounds=2,
    )

    assert workflow.max_debate_rounds == 1
