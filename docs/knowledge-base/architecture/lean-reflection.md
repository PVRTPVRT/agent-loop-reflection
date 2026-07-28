# Lean Reflection policy

Machine checks, not an LLM opinion, are the correctness gate for generated
tests. The Critic performs one advisory coverage review and cannot trigger an
unbounded suite-expansion loop.

Role budgets:

| Role | Maximum output tokens |
| --- | ---: |
| Tester | 4,000 |
| Critic | 500 |
| Coder | 2,000 |

The expected successful path is three paid calls:

```text
Tester -> Critic -> Coder
```

The local Oracle, contract validator, Docker Verifier, and hidden benchmark do
not consume model tokens.
