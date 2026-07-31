# ADR-004: Managed Repository Verification

## Status

Accepted on 2026-07-31.

## Context

ADR-003 introduced typed repository patches and test commands but intentionally stopped
before claiming repository-level execution. The existing function evaluator already had
a named-container lifecycle with network, capability, filesystem, and resource controls.
Adding a separate repository sandbox would duplicate that security-critical lifecycle
and create a fourth sandbox layer.

Repository evaluation also needs a trustworthy base. Letting a generated patch choose an
arbitrary host directory would turn the verifier into a filesystem access primitive.

## Decision

Repository verification uses four explicit stages:

```text
trusted fixture + content fingerprint
        -> disposable copy
        -> validated git apply
        -> tokenized test command in Managed Docker
```

- `RepositoryFixture` binds a curated repository ID to a local directory and a SHA-256
  content fingerprint.
- `RepositoryPatchArtifact` must name that repository ID and exact base revision.
- The verifier rejects unknown or stale revisions before copying or executing anything.
- Fixtures declare protected test paths; candidate patches touching those paths fail before
  `git apply`, preventing test deletion or weakening.
- Text patches are bounded in size and reject NUL bytes, binary patches, symlink modes,
  absolute paths, Windows drive paths, backslashes, and parent traversal.
- `git apply --check` runs before `git apply`; both receive direct argv tokens and operate
  only on a disposable copy.
- `TestCommandSpec` remains a trusted, tokenized command contract. It is never joined into
  a shell string.
- Function and repository evaluation share `ManagedDockerSandboxV2.execute_workspace`.
  Containers are named, network-disabled, capability-dropped, resource-limited, and
  removed in `finally`.
- The candidate workspace is mounted read-only during test execution. Temporary writes
  must use the container `/tmp` tmpfs.

## Consequences

- A repository patch can now be verified end to end without running candidate code on the
  host.
- Correct and non-fixing patches can be used as a deterministic mutation corpus before
  any LLM experiment.
- Fixture changes automatically invalidate stale candidate revisions.
- The first implementation supports text patches and commands available in the pinned
  Python sandbox image. Binary patches, symlinks, dependency installation, and networked
  builds deliberately fail closed.
- The older function harness still lives in `sandbox_v2.py`; a later internal cleanup can
  move it into the shared Managed module without changing the repository boundary.
