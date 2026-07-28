# Direct versus Reflection paired pilot

## Scope

This is a representative paired pilot, not yet a statistical-significance
claim. Both strategies run the same four tasks with the same model and hidden
evaluation suites:

1. `add-001`: basic numeric behavior;
2. `factorial-001`: boundary and required error behavior;
3. `palindrome-001`: string normalization;
4. `deduplicate-001`: collection semantics and stable ordering.

## Controls

- Model: `gpt-5.4-nano`
- Reasoning effort: `none`
- Direct and Reflection share the same provider implementation.
- Both are scored only against the same versioned hidden evaluation suites.
- Reflection receives public behavior contracts, never hidden test values.
- Failures are isolated per task and checkpoints are saved incrementally.

## Command

```powershell
.\scripts\run-comparison-pilot.cmd
```

## Interpretation boundary

Four paired tasks can reveal engineering trends in pass rate, cost, latency,
and call count. More tasks and repeated runs are required before making claims
about statistical significance or model-wide generalization.
