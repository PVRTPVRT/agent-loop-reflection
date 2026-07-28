# Adaptive V2 result

## Configuration

- Dataset: `coding-v2-full` (8 tasks)
- Routing suites: `coding-v2-routing` (public and separate from hidden tests)
- Model: `gpt-5.4-nano`
- Reasoning effort: `none`
- Request timeout: 60 seconds
- SDK retries: 0

## Result

| Metric | Value |
| --- | ---: |
| Hidden benchmark pass | 8/8 |
| Routing-suite pass | 8/8 |
| Direct paths | 8 |
| Reflection fallbacks | 0 |
| Calls/task | 1.0 |
| Tokens/task | 152.4 |
| Duration/task | 3.32 s |
| Total input tokens | 602 |
| Total output tokens | 617 |
| Estimated cost | $0.00089165 |

Every Direct candidate passed its independent public routing suite and then
passed the hidden V2 benchmark. No hidden test value was used to make a routing
decision.

## Baseline comparison

| Strategy | Pass | Calls/task | Tokens/task | Duration/task |
| --- | ---: | ---: | ---: | ---: |
| Direct repeated baseline | 24/24 | 1.0 | 138.7 | 2.38 s |
| Always-on Lean Reflection | 18/24 | 2.46 | 2,486.2 | 49.43 s |
| Adaptive run | 8/8 | 1.0 | 152.4 | 3.32 s |

The adaptive policy retained Direct-level cost and availability on these easy
tasks. Its additional latency versus Direct is the deliberate cost of running
the separate public routing suite before hidden evaluation.

## Interpretation

This dataset did not require a live Reflection fallback because Direct passed
all public routing gates. The fallback branch is covered by deterministic
offline tests. Future benchmark growth should add harder tasks that produce
real route failures, rather than intentionally corrupting Direct output in the
paid experiment.
