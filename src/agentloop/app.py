"""Application composition root."""

from __future__ import annotations

from agentloop.agents import CoderAgent, CriticAgent, TesterAgent
from agentloop.config import AppSettings
from agentloop.llm import OpenAIResponsesProvider
from agentloop.verifier import SandboxCodeVerifier
from agentloop.workflow import ReflectionWorkflow


def build_workflow(settings: AppSettings) -> ReflectionWorkflow:
    provider = OpenAIResponsesProvider(
        api_key=settings.require_api_key(),
        default_model=settings.model,
    )
    return ReflectionWorkflow(
        tester=TesterAgent(provider),
        critic=CriticAgent(provider),
        coder=CoderAgent(provider),
        verifier=SandboxCodeVerifier(),
        max_debate_rounds=settings.max_debate_rounds,
        max_coding_rounds=settings.max_coding_rounds,
    )
