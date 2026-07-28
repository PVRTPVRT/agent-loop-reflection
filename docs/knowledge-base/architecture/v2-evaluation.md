# V2 evaluation architecture

## Test outcomes

Every test case has both fields:

- `expected`: the expected return value, or `null` for an exception case;
- `expected_exception`: the required exception class name, or `null` for a
  value case.

The Docker harness treats the exception type as a first-class assertion.

## Generated-suite trust boundary

Model-generated tests are untrusted. Before Critic or Coder sees them:

1. Pydantic validates the V2 shape.
2. Public contracts validate function name, arity, input types, finiteness,
   hashability, and exception conditions.
3. Trusted local oracles validate each expected value.
4. Invalid suites are returned to Tester with a concrete machine error.

Hidden benchmark examples are not included in public contracts or model
prompts.

## Runtime boundaries

- API calls have explicit timeout and SDK retry budgets.
- Docker uses named containers.
- Containers are forcibly removed in a `finally` block on success, failure,
  timeout, or interruption.
- Benchmark results checkpoint after every task.

These boundaries prevent one invalid generated test, network stall, or runaway
program from blocking or destroying the rest of an experiment.
