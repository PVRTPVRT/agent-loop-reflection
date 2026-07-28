# Public contract validation result

## Result

- Internal workflow: passed
- Hidden benchmark: passed
- Debate rounds: 1
- Coding rounds: 1
- Model calls: 3
- Input tokens: 1,463
- Output tokens: 454
- Total tokens: 1,917
- Duration: 9.6 seconds
- Estimated cost: `$0.0008601`

The observed successful path was:

```text
Tester -> Critic -> Coder -> Verifier
```

The Verifier is local and does not make a model call, so the paid model-call
count was three.

## Comparison

| Version | Calls | Tokens | Duration | Estimated cost |
| --- | ---: | ---: | ---: | ---: |
| Initial structured Reflection | 6 | 7,183 | 30.4 s | $0.004133 |
| Grounded and observable | 5 | 3,412 | 15.5 s | $0.0014951 |
| Robust approval protocol | 5 | 3,127 | 12.5 s | $0.00133415 |
| Public contract | 3 | 1,917 | 9.6 s | $0.0008601 |

Relative to the initial structured run, the public-contract version used about
73% fewer tokens and cost about 79% less while preserving both internal and
hidden-benchmark success.

## Leakage check

The public `add-001` contract states accepted domains and behavior only. It does
not contain concrete hidden benchmark inputs or expected values. Any overlap
between generated tests and simple arithmetic benchmark cases is model-generated
and not supplied through the public contract.
