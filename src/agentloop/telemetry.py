"""Optional OpenTelemetry tracing with a Phoenix-compatible OTLP default."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from functools import wraps
from typing import Any

DEFAULT_PHOENIX_TRACES_ENDPOINT = "http://localhost:6006/v1/traces"
TRUTHY = {"1", "true", "yes", "on"}
FALSY = {"0", "false", "no", "off", ""}

_provider: Any | None = None
_tracer: Any | None = None


class TelemetryConfigurationError(RuntimeError):
    """Raised when telemetry was explicitly enabled but cannot be configured."""


class _NoOpSpan:
    def set_attribute(self, name: str, value: Any) -> None:
        return None

    def record_exception(self, exception: BaseException) -> None:
        return None


def _parse_enabled(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in TRUTHY:
        return True
    if normalized in FALSY:
        return False
    raise TelemetryConfigurationError(
        "AGENTLOOP_OTEL_ENABLED must be one of: 1, 0, true, false, yes, no, on, off"
    )


def _clean_attributes(
    attributes: Mapping[str, Any] | None,
) -> dict[str, str | bool | int | float]:
    cleaned: dict[str, str | bool | int | float] = {}
    for key, value in (attributes or {}).items():
        if value is None:
            continue
        if isinstance(value, (str, bool, int, float)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def configure_telemetry(
    *,
    enabled: bool | None = None,
    span_exporter: Any | None = None,
    use_batch: bool = True,
    service_name: str | None = None,
    endpoint: str | None = None,
) -> bool:
    """Configure an isolated tracer provider when tracing is explicitly enabled."""
    global _provider, _tracer

    if _provider is not None:
        return True
    is_enabled = (
        _parse_enabled(os.environ.get("AGENTLOOP_OTEL_ENABLED"))
        if enabled is None
        else enabled
    )
    if not is_enabled:
        return False

    try:
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
            SimpleSpanProcessor,
        )
    except ImportError as exc:
        raise TelemetryConfigurationError(
            "OpenTelemetry is enabled but not installed. "
            'Run: python -m pip install -e ".[observability]"'
        ) from exc

    if span_exporter is None:
        exporter_name = os.environ.get("AGENTLOOP_OTEL_EXPORTER", "otlp").strip().lower()
        if exporter_name == "console":
            span_exporter = ConsoleSpanExporter()
        elif exporter_name == "otlp":
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )
            except ImportError as exc:
                raise TelemetryConfigurationError(
                    "The OTLP HTTP exporter is missing. "
                    'Run: python -m pip install -e ".[observability]"'
                ) from exc
            trace_endpoint = (
                endpoint
                or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
                or DEFAULT_PHOENIX_TRACES_ENDPOINT
            )
            span_exporter = OTLPSpanExporter(endpoint=trace_endpoint)
        else:
            raise TelemetryConfigurationError(
                "AGENTLOOP_OTEL_EXPORTER must be 'otlp' or 'console'"
            )

    resource = Resource.create(
        {
            SERVICE_NAME: service_name
            or os.environ.get("OTEL_SERVICE_NAME")
            or "agent-loop-reflection",
            "service.namespace": "agentloop",
            "openinference.project.name": os.environ.get(
                "PHOENIX_PROJECT_NAME",
                "agent-loop-reflection",
            ),
        }
    )
    provider = TracerProvider(resource=resource)
    processor_type = BatchSpanProcessor if use_batch else SimpleSpanProcessor
    provider.add_span_processor(processor_type(span_exporter))
    _provider = provider
    _tracer = provider.get_tracer("agentloop", "0.3")
    return True


def shutdown_telemetry() -> None:
    """Flush configured spans and restore the module to its disabled state."""
    global _provider, _tracer

    provider = _provider
    _provider = None
    _tracer = None
    if provider is not None:
        provider.force_flush(timeout_millis=5_000)
        provider.shutdown()


@contextmanager
def telemetry_session() -> Iterator[bool]:
    """Own telemetry configuration for one CLI run and always flush on exit."""
    already_configured = _provider is not None
    enabled = configure_telemetry()
    try:
        yield enabled
    finally:
        if enabled and not already_configured:
            shutdown_telemetry()


@contextmanager
def traced_span(
    name: str,
    attributes: Mapping[str, Any] | None = None,
) -> Iterator[Any]:
    """Create a span when enabled, otherwise return a zero-cost compatible handle."""
    tracer = _tracer
    if tracer is None:
        yield _NoOpSpan()
        return

    with tracer.start_as_current_span(
        name,
        attributes=_clean_attributes(attributes),
    ) as span:
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_attribute("error.type", type(exc).__name__)
            raise


def set_span_attributes(span: Any, attributes: Mapping[str, Any]) -> None:
    for key, value in _clean_attributes(attributes).items():
        span.set_attribute(key, value)


def traced_task_method(span_name: str) -> Callable:
    """Trace strategy/workflow methods without recording prompts, code, or tests."""

    def decorate(function: Callable) -> Callable:
        @wraps(function)
        def wrapped(self, task, *args, **kwargs):
            with traced_span(
                span_name,
                {
                    "agentloop.task.id": getattr(task, "task_id", "unknown"),
                    "agentloop.component": getattr(self, "name", type(self).__name__),
                },
            ) as span:
                result = function(self, task, *args, **kwargs)
                attributes = {
                    "agentloop.success": getattr(result, "success", None),
                    "agentloop.internal_success": getattr(
                        result,
                        "internal_success",
                        None,
                    ),
                    "agentloop.coding_rounds": getattr(
                        result,
                        "coding_rounds",
                        None,
                    ),
                    "agentloop.debate_rounds": getattr(
                        result,
                        "debate_rounds",
                        None,
                    ),
                    "agentloop.duration_ms": getattr(result, "duration_ms", None),
                }
                usage = getattr(result, "usage", None)
                if usage is not None:
                    attributes.update(
                        {
                            "gen_ai.usage.input_tokens": usage.input_tokens,
                            "gen_ai.usage.output_tokens": usage.output_tokens,
                            "gen_ai.usage.total_tokens": usage.total_tokens,
                            "gen_ai.request.model_calls": usage.model_calls,
                        }
                    )
                set_span_attributes(span, attributes)
                return result

        return wrapped

    return decorate


def traced_verification_method(span_name: str = "agentloop.verify") -> Callable:
    """Trace a verifier call without attaching candidate code or test inputs."""

    def decorate(function: Callable) -> Callable:
        @wraps(function)
        def wrapped(self, code, suite, *args, **kwargs):
            with traced_span(
                span_name,
                {
                    "code.function.name": getattr(suite, "function_name", "unknown"),
                    "test.case.count": len(getattr(suite, "test_cases", ())),
                },
            ) as span:
                result = function(self, code, suite, *args, **kwargs)
                set_span_attributes(
                    span,
                    {"agentloop.verification.success": result.success},
                )
                return result

        return wrapped

    return decorate
