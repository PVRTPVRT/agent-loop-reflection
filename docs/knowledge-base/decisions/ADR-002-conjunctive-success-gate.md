# ADR-002: Conjunctive Success Gate

## Status

Accepted on 2026-07-28.

## Context

The first v0.2 pilot produced a repaired candidate that still failed the public routing
suite, while an insufficient hidden suite passed it. Treating hidden verification as
the only final signal created a false positive.

## Decision

For Adaptive and Repair Replay, a result is successful only when both conditions hold:

```text
internal route acceptance AND independent hidden acceptance
```

Repair retries must carry the current candidate and latest verifier message. A failed
internal route cannot be overridden by a later hidden-suite pass.

## Consequences

- False positives from a blind hidden suite fail closed.
- Routing suites become part of the release acceptance contract.
- Trace artifacts retain both internal and hidden verification outcomes.
- A bad routing expectation can now cause a false negative, so routing suites must be
  pre-registered, reviewed, and checked against a trusted Oracle.
