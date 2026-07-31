# Optional OpenTelemetry and Phoenix tracing

Agent Loop Reflection keeps JSON experiment traces as the auditable source of truth.
OpenTelemetry is an optional operational view of the same execution, not a replacement for
versioned benchmark reports.

## Span tree

An Adaptive task emits this hierarchy when telemetry is enabled:

```text
agentloop.adaptive.task
├── agentloop.llm.generate          # Direct
├── agentloop.verify                # public routing suite
└── agentloop.repair.workflow       # only after routing failure
    ├── agentloop.llm.generate      # Critic
    ├── agentloop.llm.generate      # Coder
    └── agentloop.verify            # repair route
```

The final hidden verification is another `agentloop.verify` child of the task span.
Repair Replay uses `agentloop.repair_replay.task` as its root.

Spans include task ID, role, model, token usage, latency, round count, test-case count, and
success state. They deliberately exclude prompts, generated code, test arguments, API keys,
and verifier messages.

## Install the optional exporter

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[observability]"
```

The core package works without this extra. Explicitly enabling telemetry without installing
the extra produces a configuration error instead of silently disabling traces.

## Run Phoenix locally

The repository includes a reproducible Docker Compose configuration for Phoenix 19.11.0.
The OCI digest is pinned, ports are bound to localhost, the SQLite data directory uses a
named volume, and Compose waits for an HTTP health check.

```powershell
.\scripts\start-phoenix.cmd
```

The script opens <http://localhost:6006> after the service becomes healthy. Stop the service
without deleting its persistent volume:

```powershell
.\scripts\stop-phoenix.cmd
```

A workstation that already has the earlier `agentloop-phoenix` demo container can keep using
it. To switch to the persistent Compose service without deleting the old container:

```powershell
docker stop agentloop-phoenix
.\scripts\start-phoenix.cmd
```

Add these values to `.env`:

```dotenv
AGENTLOOP_OTEL_ENABLED=true
AGENTLOOP_OTEL_EXPORTER=otlp
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:6006/v1/traces
OTEL_SERVICE_NAME=agent-loop-reflection
PHOENIX_PROJECT_NAME=agent-loop-reflection
```

Run a versioned script, then open <http://localhost:6006>:

```powershell
scripts\run-v0.3-hard-matrix-pilot.cmd
```

For exporter debugging without Phoenix, set `AGENTLOOP_OTEL_EXPORTER=console`.

## Failure behavior

- Telemetry is disabled by default.
- Export is batch processed and flushed when the CLI exits.
- An unavailable collector may report export errors, but does not alter benchmark scoring.
- JSON reports and traces remain available when OpenTelemetry is disabled or unavailable.

References:

- [OpenTelemetry Python exporters](https://opentelemetry.io/docs/languages/python/exporters/)
- [OpenTelemetry OTLP exporter configuration](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/)
- [Phoenix Docker deployment](https://arize.com/docs/phoenix/self-hosting/deployment-options/docker)
- [Phoenix server ports](https://arize.com/docs/phoenix/self-hosting/configuration)
