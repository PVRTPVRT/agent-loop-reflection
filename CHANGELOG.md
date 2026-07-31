# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A typed artifact/evaluation boundary for source code, repository patches, function
  cases, and sandboxed test-command specifications.
- A generic verifier protocol with an adapter for the existing function-case verifier.

### Changed

- Adaptive, evidence-driven repair, and recorded-failure replay now pass typed artifacts
  and evaluation specifications while retaining the v0.3 constructor interface.
- The installed `agentloop` command and `python -m agentloop` now use the single V2
  Direct/Reflection/Adaptive dispatcher.
- Deterministic and Docker test stages no longer execute Managed Docker tests twice.

### Removed

- Twenty production-unreachable v0.1 portability, contract, comparison, and transitional
  CLI modules; their released history remains available from the `v0.1.0` and `v0.2.0`
  tags.
- Ten test files that exclusively exercised those removed historical modules.

### Security

- Test-command specifications reject blank tokens, absolute or escaping working
  directories, unbounded timeouts, and network-enabled execution.

## [0.3.0] - 2026-07-31

### Added

- A three-task hard benchmark matrix covering TTL/LRU state, chunked frame decoding,
  and idempotent ledger processing.
- Versioned public contracts, routing suites, trusted fixtures, data fingerprints, and
  experiment-lineage tests for the v0.3 benchmark.
- Repair-attempt history so later Critic and Coder rounds receive prior patches and their
  latest verifier failures.
- Optional vendor-neutral OpenTelemetry tracing with a Phoenix-compatible OTLP/HTTP
  default and an explicit observability dependency extra.
- Reproducible local Phoenix configuration with a pinned image digest, persistent storage,
  health checks, and Windows start/stop scripts.

### Changed

- Public documentation now separates natural Adaptive experiments, recorded-failure
  replay, and prompt-only counter-evidence.
- Portfolio evidence now reports the natural 2/3 hard-matrix result instead of presenting
  a repair replay as a general success-rate claim.
- The package version and release documentation are aligned at v0.3.0.

### Fixed

- Preserve every failed repair candidate and verifier message across bounded retries
  instead of exposing only the latest candidate.

### Security

- OpenTelemetry spans deliberately exclude prompts, generated code, test arguments,
  verifier messages, and API credentials.
## [0.2.0] - 2026-07-28

### Added

- Immutable `RepairContext` carrying the failed Direct candidate, frozen routing suite,
  and verifier evidence into the repair workflow.
- Evidence-driven Critic and Coder roles that diagnose and patch the current candidate.
- Recorded Failure Replay as a separately labelled experiment for deterministic repair
  branch validation.
- A hard TTL/LRU state-machine pilot, trusted Oracle, public routing cases, R2 hidden
  dataset, and reproducible failure fixture.
- Repair traces for context receipt, diagnosis, code repair, routing verification, and
  independent hidden verification.
- Regression tests for iterative repair state and false-positive prevention.

### Changed

- Adaptive final success now requires both internal route acceptance and independent
  hidden-suite acceptance.
- Every repair retry re-diagnoses the latest candidate using the latest verifier message.
- v0.2 public documentation distinguishes natural Adaptive results from failure replay
  results and records the invalidated R1 false positive.

### Fixed

- Prevent a failed internal repair from being reported as successful when an insufficient
  hidden suite happens to pass the candidate.
- Prevent later repair rounds from restarting from the original failed candidate.
- Validate TTL/LRU expiry independently of LRU iteration order.

## [0.1.0] - 2026-07-28

### Added

- Direct, Lean Reflection, and Adaptive coding-agent strategies.
- Versioned benchmark datasets, public contracts, and routing policies.
- Repeated Direct versus Reflection experiments with cost and quality metrics.
- Typed evaluation schemas with `expected_exception` support.
- Managed Docker sandboxing with non-root, read-only, network-disabled execution.
- GitHub Actions quality and Docker integration pipelines.
- Architecture decisions and versioned experiment reports.

### Security

- Validate generated tests against public contracts before execution.
- Enforce container cleanup, resource limits, dropped capabilities, and no-new-privileges.
- Keep API credentials outside version control through `.env` exclusion.
