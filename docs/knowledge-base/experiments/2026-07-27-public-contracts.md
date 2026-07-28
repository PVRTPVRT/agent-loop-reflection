# Public task contracts

## Goal

Remove semantic ambiguity without revealing hidden benchmark examples.

## Design

Each benchmark task now has a versioned public contract containing:

- required function name;
- parameter names and accepted domains;
- return behavior;
- explicitly required errors.

Tester and Critic receive the same contract. Concrete hidden inputs and expected
values remain only in the evaluation dataset and are not included in prompts.

For `add-001`, the public domain explicitly states `integer or finite float`.
This prevents the Critic from incorrectly rejecting valid floating-point tests.

## Safety invariant

Public contracts describe behavior but contain no hidden test values. Tests
verify that all dataset tasks have contracts and that representative hidden
float values are absent from the rendered `add-001` contract.
