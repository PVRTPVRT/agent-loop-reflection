# Direct versus Reflection paired pilot result

## Aggregate result

| Strategy | Pass | Calls/task | Tokens/task | Duration/task |
| --- | ---: | ---: | ---: | ---: |
| Direct | 4/4 | 1.0 | 119.5 | 2.94 s |
| Reflection | 4/4 | 5.0 | 4,062.3 | 14.34 s |

Both strategies achieved 100% hidden-benchmark pass rate. Reflection therefore
provided no measured accuracy gain on this four-task pilot while using about
34x as many tokens and taking about 4.9x as long.

## Cost

At the GPT-5.4 nano rates used by this experiment:

| Strategy | Input | Output | Estimated cost |
| --- | ---: | ---: | ---: |
| Direct | 277 | 201 | $0.00030665 |
| Reflection | 12,382 | 3,867 | $0.00731015 |
| Total | 12,659 | 4,068 | $0.00761680 |

Reflection cost about 23.8x as much as Direct in this run.

## Per-task result

| Task | Direct | Reflection | Reflection calls | Internal success |
| --- | ---: | ---: | ---: | ---: |
| add | pass | pass | 5 | true |
| factorial | pass | pass | 6 | false |
| palindrome | pass | pass | 3 | true |
| deduplicate | pass | pass | 6 | false |

## Diagnosed internal failures

### Factorial

The internal test model cannot represent an expected exception. The generated
suite used `expected: null` for negative inputs, but the verifier treats any
raised `ValueError` as an execution failure. It also generated a placeholder
string for `100!`, which no correct implementation could satisfy.

The hidden suite did not test the required negative-input error, so external
success currently overstates contract coverage.

### Deduplicate

The generated suite included unhashable nested lists even though the public
contract requires hashable elements. It also expected `1`, `True`, and `False`
to remain distinct, conflicting with Python equality/hash semantics where
`1 == True` and `0 == False`.

## Interpretation

This pilot supports an engineering conclusion, not a statistical-significance
claim: Reflection is currently inefficient on easy tasks, and its generated
tests can be less reliable than the code it evaluates.

Before expanding the experiment, the benchmark/test schema should support
expected exceptions and validate generated suites against public contracts.
Otherwise a larger run would measure known harness defects rather than the
value of reflection.
