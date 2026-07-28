# Coding V2 full repeated-experiment protocol

- Dataset: eight versioned tasks in `coding-v2-full.json`
- Model: `gpt-5.4-nano`
- Reasoning: `none`
- Strategies: Direct and Lean Reflection
- Repetitions: three independent API runs per strategy
- Primary metric: hidden-suite pass rate
- Secondary metrics: internal/external agreement, calls, tokens, latency, cost,
  and suite-normalization corrections
- Exception coverage: factorial negative input, fibonacci negative input, and
  clamp invalid interval

Three repetitions over eight tasks produce 24 task observations per strategy.
This is still a small engineering benchmark, but it is materially stronger than
the four-task single-run pilot and can expose run-to-run instability.
