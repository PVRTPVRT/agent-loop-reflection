# Resume-ready project points

## Project summary

Built an observable and cost-aware coding-agent evaluation system that compares
Direct generation, always-on Reflection, and adaptive Direct-to-Reflection
routing under versioned Docker-isolated benchmarks.

## Evidence-backed bullets

- Designed a V2 evaluation schema with first-class expected-exception
  assertions and machine-checkable public task contracts.
- Added trusted local Oracles that corrected or rejected 41 semantically
  invalid model-generated test outcomes across repeated experiments.
- Implemented managed Docker execution with network isolation, resource limits,
  hard timeouts, and guaranteed container cleanup.
- Ran 48 paired task observations across Direct and Lean Reflection:
  Direct achieved 24/24 while always-on Reflection achieved 18/24 under a
  60-second request SLO, exposing multi-call timeout amplification.
- Reduced a validated Reflection path from 6 calls and 7,183 tokens to 3 calls
  and roughly 3,000 tokens per task through structured outputs, public
  contracts, deterministic normalization, and role budgets.
- Implemented adaptive routing with independent public gate suites; achieved
  8/8 hidden-benchmark passes at one model call per task and an estimated
  `$0.00089` total API cost.

## Technology stack

Python 3.12, Pydantic, OpenAI Responses API, Structured Outputs/JSON Schema,
Docker, pytest, Ruff, typed provider interfaces, versioned benchmark datasets,
incremental checkpoints, and per-agent execution traces.
