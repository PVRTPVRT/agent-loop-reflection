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

## Known legacy limitation

The original `DockerSandboxV2` integration test exercises the pre-managed
`docker run --rm` implementation, which can leave a container behind when the
Docker client is interrupted on Windows. Production V2 experiment entry points
use `ManagedDockerSandboxV2`; routine regression commands should exclude the
legacy integration test until the old module is removed during repository
cleanup.
