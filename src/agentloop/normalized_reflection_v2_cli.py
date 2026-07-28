"""Bounded V2 runner with deterministic suite normalization."""

from __future__ import annotations

import sys

from agentloop import reflection_v2_cli
from agentloop.normalized_evaluation import (
    NormalizedEvaluationTesterAgent,
    NormalizedEvaluationWorkflow,
)


def main(argv: list[str] | None = None) -> int:
    reflection_v2_cli.EvaluationTesterAgent = NormalizedEvaluationTesterAgent
    reflection_v2_cli.EvaluationReflectionWorkflow = NormalizedEvaluationWorkflow
    return reflection_v2_cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
