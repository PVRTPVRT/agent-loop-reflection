# Internal trace and test grounding

## Motivation

The first successful nano Reflection smoke test passed the hidden benchmark but
reported `internal_success=false`. The benchmark report did not retain the
generated test suite or per-round verifier messages, so the exact failing case
could not be reconstructed.

## Changes

- Added grounded Tester instructions that prohibit requirements not stated by
  the task.
- Added a Critic rule that rejects invented type checks, exceptions, special
  floating-point cases, and return formats.
- Added an observable Reflection strategy that stores:
  - the original task and hidden evaluation suite;
  - the generated internal test suite;
  - every Tester, Critic, Coder, and Verifier event;
  - internal and external verification outcomes;
  - final code and usage metrics.
- Traces are written per task under `benchmarks/traces/`.

## Command

```powershell
.\scripts\run-observable-portability.cmd --limit 1
```
