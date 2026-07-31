from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

import pytest

pytest.importorskip("opentelemetry.sdk")

from agentloop.telemetry import (
    configure_telemetry,
    shutdown_telemetry,
    traced_span,
)


class RecordingHandler(BaseHTTPRequestHandler):
    requests: ClassVar[list[tuple[str, str, bytes]]] = []

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        body = self.rfile.read(length)
        self.requests.append(
            (
                self.path,
                self.headers.get("Content-Type", ""),
                body,
            )
        )
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args) -> None:
        return None


@pytest.fixture(autouse=True)
def clean_telemetry():
    shutdown_telemetry()
    RecordingHandler.requests = []
    yield
    shutdown_telemetry()


def test_real_otlp_http_exporter_posts_protobuf_to_configured_trace_endpoint() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), RecordingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}/v1/traces"

    try:
        configure_telemetry(
            enabled=True,
            endpoint=endpoint,
            use_batch=False,
            service_name="otlp-http-test",
        )
        with traced_span("agentloop.otlp.test", {"agentloop.task.id": "offline"}):
            pass
    finally:
        shutdown_telemetry()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert len(RecordingHandler.requests) == 1
    path, content_type, body = RecordingHandler.requests[0]
    assert path == "/v1/traces"
    assert content_type == "application/x-protobuf"
    assert len(body) > 0
