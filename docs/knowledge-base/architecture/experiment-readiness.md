# Experiment readiness

## Ready

- V2 datasets and contracts are versioned.
- Hidden suites include required exception behavior.
- Generated test suites are schema-valid, contract-valid, and Oracle-normalized.
- Docker containers are named and cleaned in `finally`.
- API requests have explicit timeout and retry budgets.
- Per-task checkpointing and traces are available.
- Direct and Lean Reflection have repeatable CLI entry points.

## Recommended next research direction

Use adaptive routing:

1. Generate once with Direct.
2. Run local hidden or development verification.
3. Return immediately on success.
4. Invoke Reflection only on a failed verification or high-complexity policy.

The repeated V2 results show that always-on Reflection is not economical for
easy tasks and reduces end-to-end availability through additional API calls.

## Current execution boundary

Docker responsibilities are now narrow: `sandbox.py` prepares the runtime,
`sandbox_v2.py` builds and parses the function harness, and
`managed_sandbox_v2.py` owns the only container lifecycle used by both function and
repository evaluation. The interrupt-prone `docker run --rm` path has been removed.