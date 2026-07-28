# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-28

### Added

- Direct, Lean Reflection, and Adaptive coding-agent strategies.
- Versioned benchmark datasets, public contracts, and routing policies.
- Repeated Direct versus Reflection experiments with cost and quality metrics.
- Typed evaluation schemas with `expected_exception` support.
- Managed Docker sandboxing with non-root, read-only, network-disabled execution.
- GitHub Actions quality and Docker integration pipelines.
- Local knowledge base, architecture decisions, experiment reports, and resume points.

### Security

- Validate generated tests against public contracts before execution.
- Enforce container cleanup, resource limits, dropped capabilities, and no-new-privileges.
- Keep API credentials outside version control through `.env` exclusion.
