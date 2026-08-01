# ADR-003: Artifact and Evaluation Boundary

## Status

Accepted on 2026-07-31.

## Context

The v0.3 workflow proved a bounded repair loop on single Python functions. Its core
interfaces still passed two concrete values everywhere: a source-code string and an
`EvaluationSuite` containing positional function calls.

Adding more tasks with that same shape would increase sample count, but it would not
prove that the architecture can support repository patches, existing test suites, or
multi-file changes. Implementing those task types directly in each strategy would also
duplicate dispatch and migration logic across Adaptive, Repair, and Replay.

## Decision

Introduce one typed boundary between generated candidates and verification:

- `CandidateArtifact` is a discriminated union. v0.4 defines source-code and repository-
  patch variants.
- `EvaluationSpec` is a discriminated union. v0.4 defines function-case and test-command
  variants.
- `ArtifactVerifier.verify_artifact(artifact, spec)` is the generic verification
  protocol.
- One compatibility adapter maps the current source-code/function-case pair to the
  existing `verify(code, suite)` interface.
- `RepairContext` stores only the generic artifact and specification. Read-only
  `failed_code` and `routing_suite` properties preserve current agent compatibility
  without duplicating state.

The executable v0.4 path remains deliberately narrow:

```text
SourceCodeArtifact + FunctionCaseSpec -> existing managed Docker verifier
```

`RepositoryPatchArtifact` and `TestCommandSpec` are accepted as typed repair evidence,
but no repository executor is claimed yet. A source-only workflow encountering either
variant fails explicitly with `UnsupportedEvaluationBoundaryError`.

## Security Constraints

`TestCommandSpec` is a data contract, not a shell string:

- command arguments are stored as non-empty tokens;
- working directories must be relative and cannot escape the candidate workspace;
- timeouts are bounded;
- network access is fixed to disabled.

The future repository executor must pass tokens directly to a process runner. It must
not concatenate them into a shell command.

## Consequences

- Existing Direct, Adaptive, Repair, and Replay behavior remains backward compatible.
- New task types can share orchestration and trace schemas instead of forking workflows.
- Unsupported artifact/specification combinations fail closed and are visible in tests.
- The types alone do not demonstrate repository-level repair. That requires a managed
  workspace executor, repository fixtures, mutation corpus, and end-to-end evidence.

## Follow-up

1. Implement an isolated repository workspace verifier for
   `RepositoryPatchArtifact + TestCommandSpec`.
2. Add a small deterministic mutation corpus and repository-level benchmark fixtures.
3. Add property/metamorphic evaluation specifications where exact expected outputs are
   unavailable.
4. Run zero-API fixture validation before spending tokens on repeated LLM experiments.
