# Adaptive routing

## Decision flow

```text
Direct generation
    |
    v
Public routing suite in managed Docker
    | pass                         | fail
    v                              v
Hidden benchmark              Lean Reflection
                                   |
                                   v
                              Hidden benchmark
```

Routing suites are versioned public development tests. They are stored
separately from hidden benchmark suites, use different concrete arguments, and
are validated against the same public contracts and trusted Oracles.

## Why

Repeated V2 experiments showed that Direct solved all 24 task observations,
while always-on Reflection increased latency, cost, and API-timeout exposure.
Adaptive routing preserves the cheap Direct path and pays for Reflection only
when a local gate detects a concrete failure.

## Trace contract

Each adaptive task trace records:

- Direct code;
- public routing suite and its verdict;
- selected path (`direct` or `reflection`);
- Reflection events when fallback occurs;
- hidden benchmark verdict;
- total usage across both phases.
