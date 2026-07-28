from __future__ import annotations

from collections import Counter

import pytest

pytest.importorskip("opentelemetry.sdk")

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agentloop.adaptive_strategy_v2 import AdaptiveStrategyV2
from agentloop.benchmark import MeteredLLMProvider
from agentloop.contracts_v2 import ContractRegistryV2
from agentloop.evaluation_agents import EvaluationTesterAgent
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.evaluation_verifier import EvaluationCodeVerifier
from agentloop.llm import FakeLLMProvider
from agentloop.repair_agents_v2 import (
    RepairEvaluationCoderAgent,
    RepairEvaluationCriticAgent,
)
from agentloop.repair_workflow_v2 import EvidenceDrivenRepairWorkflow
from agentloop.routing_suites import RoutingSuiteRegistry
from agentloop.sandbox import ExecutionResult
from agentloop.telemetry import configure_telemetry, shutdown_telemetry


class AddSandbox:
    def execute_v2(self, code, test_suite):
        success = "return a + b" in code
        return ExecutionResult(
            success=success,
            message="passed route" if success else "expected 3, got -1",
        )


@pytest.fixture(autouse=True)
def clean_telemetry():
    shutdown_telemetry()
    yield
    shutdown_telemetry()


def test_adaptive_repair_emits_nested_operational_span_tree(tmp_path) -> None:
    exporter = InMemorySpanExporter()
    configure_telemetry(
        enabled=True,
        span_exporter=exporter,
        use_batch=False,
        service_name="span-tree-test",
    )
    provider = MeteredLLMProvider(
        FakeLLMProvider(
            [
                "def add(a, b):\n    return a - b",
                "Faulty statement: return a - b",
                "def add(a, b):\n    return a + b",
            ]
        )
    )
    contracts = ContractRegistryV2.load(
        "benchmarks/contracts/coding-v2-contracts.json"
    )
    verifier = EvaluationCodeVerifier(sandbox=AddSandbox())
    workflow = EvidenceDrivenRepairWorkflow(
        tester=EvaluationTesterAgent(provider, registry=contracts),
        critic=RepairEvaluationCriticAgent(provider, registry=contracts),
        coder=RepairEvaluationCoderAgent(provider, registry=contracts),
        verifier=verifier,
        max_coding_rounds=1,
    )
    strategy = AdaptiveStrategyV2(
        provider=provider,
        verifier=verifier,
        reflection_workflow=workflow,
        routing_suites=RoutingSuiteRegistry.load(),
        trace_dir=tmp_path,
    )
    task = EvaluationDataset.load("benchmarks/datasets/coding-v2-full.json").tasks[0]

    result = strategy.run(task)

    assert result.success is True
    spans = exporter.get_finished_spans()
    assert Counter(span.name for span in spans) == {
        "agentloop.adaptive.task": 1,
        "agentloop.repair.workflow": 1,
        "agentloop.llm.generate": 3,
        "agentloop.verify": 3,
    }
    adaptive = next(span for span in spans if span.name == "agentloop.adaptive.task")
    repair = next(span for span in spans if span.name == "agentloop.repair.workflow")
    assert repair.parent.span_id == adaptive.context.span_id

    llm_spans = [span for span in spans if span.name == "agentloop.llm.generate"]
    by_agent = {span.attributes["agentloop.agent"]: span for span in llm_spans}
    assert set(by_agent) == {"direct", "critic", "coder"}
    assert by_agent["direct"].parent.span_id == adaptive.context.span_id
    assert by_agent["critic"].parent.span_id == repair.context.span_id
    assert by_agent["coder"].parent.span_id == repair.context.span_id
    assert by_agent["critic"].attributes["agentloop.repair.round"] == "1"
    assert by_agent["coder"].attributes["agentloop.repair.round"] == "1"

    serialized = repr([dict(span.attributes) for span in spans])
    assert "return a - b" not in serialized
    assert "return a + b" not in serialized
