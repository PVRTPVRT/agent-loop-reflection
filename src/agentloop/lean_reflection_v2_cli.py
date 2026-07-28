"""Lean, normalized, bounded V2 Reflection runner."""

from __future__ import annotations

import sys

from agentloop import reflection_v2_cli
from agentloop.lean_evaluation import LeanNormalizedEvaluationWorkflow
from agentloop.normalized_evaluation import NormalizedEvaluationTesterAgent
from agentloop.role_budget_v2_llm import RoleBudgetV2Provider


def main(argv: list[str] | None = None) -> int:
    reflection_v2_cli.BoundedStrictV2Provider = RoleBudgetV2Provider
    reflection_v2_cli.EvaluationTesterAgent = NormalizedEvaluationTesterAgent
    reflection_v2_cli.EvaluationReflectionWorkflow = LeanNormalizedEvaluationWorkflow
    return reflection_v2_cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
