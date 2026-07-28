# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
