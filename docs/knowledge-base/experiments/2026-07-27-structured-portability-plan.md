# Structured portability and resilient benchmarks

## Problem

The first GPT-5.4 nano Reflection experiments repeatedly returned no parseable
Tester JSON. A failed task also aborted the whole batch before partial results
could be persisted.

## Change

- Tester requests now use Responses API Structured Outputs with a strict JSON
  Schema.
- Critic and Coder requests remain ordinary text generation.
- The portability runner isolates exceptions per task and writes a checkpoint
  after every completed or failed task.
- The default smoke test is one task with `reasoning_effort=none`.

## Validation

Run offline checks first:

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m pytest -q
```

Then run one paid portability task:

```powershell
.\scripts\run-structured-portability.cmd --limit 1
```

The result is saved to
`benchmarks/results/reflection-structured-gpt-5.4-nano.json`.
