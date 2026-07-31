from __future__ import annotations

import pytest

pytest.importorskip("opentelemetry.sdk")

from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from agentloop.benchmark import MeteredLLMProvider
from agentloop.llm import FakeLLMProvider
from agentloop.models import LLMRequest, LLMResponse, TokenUsage
from agentloop.telemetry import (
    configure_telemetry,
    shutdown_telemetry,
    traced_span,
)


@pytest.fixture(autouse=True)
def clean_telemetry():
    shutdown_telemetry()
    yield
    shutdown_telemetry()


def test_telemetry_is_disabled_without_explicit_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("AGENTLOOP_OTEL_ENABLED", raising=False)

    assert configure_telemetry() is False


def test_metered_llm_span_records_usage_but_not_prompt_content() -> None:
    exporter = InMemorySpanExporter()
    assert configure_telemetry(
        enabled=True,
        span_exporter=exporter,
        use_batch=False,
        service_name="telemetry-test",
    )
    provider = MeteredLLMProvider(
        FakeLLMProvider(
            [
                LLMResponse(
                    text="secret generated code",
                    model="fake-model",
                    usage=TokenUsage(
                        input_tokens=11,
                        output_tokens=7,
                        total_tokens=18,
                    ),
                )
            ]
        )
    )
    request = LLMRequest(
        system_prompt="private system prompt",
        user_prompt="private user prompt",
        metadata={
            "agent": "coder",
            "strategy": "adaptive",
            "task_id": "task-001",
        },
    )

    with traced_span("agentloop.test.parent"):
        provider.generate(request)

    spans = {span.name: span for span in exporter.get_finished_spans()}
    llm_span = spans["agentloop.llm.generate"]
    parent_span = spans["agentloop.test.parent"]
    assert llm_span.parent.span_id == parent_span.context.span_id
    assert llm_span.attributes["gen_ai.operation.name"] == "generate"
    assert llm_span.attributes["gen_ai.request.model"] == "fake-model"
    assert llm_span.attributes["gen_ai.usage.input_tokens"] == 11
    assert llm_span.attributes["gen_ai.usage.output_tokens"] == 7
    assert llm_span.attributes["agentloop.task.id"] == "task-001"
    serialized_attributes = repr(dict(llm_span.attributes))
    assert "private system prompt" not in serialized_attributes
    assert "private user prompt" not in serialized_attributes
    assert "secret generated code" not in serialized_attributes
