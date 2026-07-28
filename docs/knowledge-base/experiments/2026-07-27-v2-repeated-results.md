# Coding V2 repeated Direct versus Lean Reflection results

## Protocol

- Eight versioned tasks
- Three independent runs per strategy
- 24 task observations per strategy
- Model: `gpt-5.4-nano`
- Reasoning effort: `none`
- API request timeout: 60 seconds
- SDK automatic retries: 0
- Docker: named managed containers with guaranteed cleanup

## Aggregate results

| Strategy | Pass | API timeouts | Calls/task | Tokens/task | Latency/task | Estimated cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Direct | 24/24 (100%) | 0 | 1.00 | 138.7 | 2.38 s | $0.0022637 |
| Lean Reflection | 18/24 (75%) | 6 | 2.46 | 2,486.2 | 49.43 s | $0.03249805 |

Reflection used about 17.9x as many tokens, cost 14.4x as much, and took
20.8x as long per task.

All six Reflection failures were `APITimeoutError`. Among the 18 Reflection
runs that completed the model workflow, internal verification and the hidden
benchmark both passed: 18/18 agreement.

## Reflection stability by task

| Task | Passes | Timeouts |
| --- | ---: | ---: |
| add | 2/3 | 1 |
| factorial | 2/3 | 1 |
| fibonacci | 1/3 | 2 |
| palindrome | 3/3 | 0 |
| clamp | 3/3 | 0 |
| count-vowels | 2/3 | 1 |
| deduplicate | 2/3 | 1 |
| flatten-once | 3/3 | 0 |

Failures moved between tasks across repetitions, supporting the interpretation
that service/network latency, rather than deterministic task logic, caused the
observed failures.

## Oracle normalization

Across 18 successful Reflection traces:

- internal pass: 18/18;
- external pass: 18/18;
- 41 generated outcomes or cases were corrected/dropped;
- 7 traces required at least one correction;
- average validated internal suite size: 10.6 cases.

The largest correction count occurred in `count-vowels`, demonstrating that
schema-conformant output is not necessarily semantically correct. The trusted
Oracle boundary materially prevented generated-test errors from reaching the
Coder and Verifier.

## Statistical interpretation

At the task-run observation level, Direct won six discordant pairs and
Reflection won zero. An exploratory two-sided exact McNemar/binomial test gives
`p = 0.03125`. This should not be presented as broad model-level proof because
the 24 observations reuse eight tasks and are therefore not fully independent.

The defensible portfolio claim is narrower:

> On an eight-task, three-run benchmark, the validated Lean Reflection pipeline
> achieved 100% correctness conditional on completion, but only 75% end-to-end
> pass rate under a 60-second request SLO because multi-call workflows amplified
> API timeout exposure. Direct achieved 100% with substantially lower cost and
> latency.

## Decision

The V2 evaluation architecture is suitable for further experiments:

- expected exceptions are first-class;
- public contracts are machine-checkable;
- generated outcomes are normalized by trusted local Oracles;
- internal and external results are traceable;
- failures checkpoint and continue;
- API and Docker lifecycles are bounded.

For easy tasks, Direct should be the default. Reflection should be routed only
to tasks where Direct fails a local verification gate or where task complexity
justifies the additional calls.
