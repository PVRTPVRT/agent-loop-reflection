# Robust Critic approval protocol

## Problem

The Critic sometimes explains its reasoning and then ends with `[APPROVED]`.
The original implementation required the whole response to exactly equal the
marker, which incorrectly triggered another Tester/Critic debate round.

## Rule

An approval is valid only when `[APPROVED]` is the final non-empty line.

This accepts:

```text
The suite matches the task contract.

[APPROVED]
```

It rejects:

```text
Do not output [APPROVED], because an edge case is missing.
```

and:

```text
[APPROVED]
However, an edge case is still missing.
```

## Expected impact

For an already-correct suite, the Reflection path should require three model
calls: Tester, Critic, and Coder.
