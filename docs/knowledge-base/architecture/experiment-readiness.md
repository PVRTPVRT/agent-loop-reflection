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

## Known infrastructure debt

Docker preparation, the function-case harness, and managed container cleanup are still
split across `sandbox.py`, `sandbox_v2.py`, and `managed_sandbox_v2.py`. Production V2
entry points use `ManagedDockerSandboxV2`, but the layering is wider than necessary.
The repository executor should consolidate both function and repository evaluation onto
one named-container lifecycle rather than adding a fourth sandbox implementation.
