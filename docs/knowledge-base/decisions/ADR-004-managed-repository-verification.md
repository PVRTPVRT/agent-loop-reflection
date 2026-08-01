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

- `RepositoryFixture` binds a curated repository ID to a local directory and the complete
  256-bit SHA-256 content fingerprint.
- `RepositoryPatchArtifact` must name that repository ID and exact base revision.
- The verifier rejects unknown revisions before copying. The disposable copy is then
  re-fingerprinted, so a fixture changed after registration fails before patch application.
- `copytree(symlinks=True)` preserves links in the disposable copy and fingerprinting
  rejects them, preventing a changed fixture from being followed outside its root.
- Fixtures declare protected test paths. Header parsing rejects direct changes before
  `git apply`; full protected-file fingerprints are compared again afterward, catching
  rename/deletion forms that bypass the lightweight parser.
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
- The versioned `repository-v0.4` dataset exercises Calculator and Frame Decoder with
  correct and non-fixing patches; all four expected outcomes are committed before any
  LLM experiment.
- Fixture changes automatically invalidate stale candidate revisions and committed report lineage.
- The first implementation supports text patches and commands available in the pinned
  Python sandbox image. Binary patches, symlinks, dependency installation, and networked
  builds deliberately fail closed.
- Docker runtime preparation, function harness construction, and Managed lifecycle are
  separate responsibilities; the old `docker run --rm` execution path is removed.
