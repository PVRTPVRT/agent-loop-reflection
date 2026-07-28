"""Per-role output budgets for the bounded V2 provider."""

from __future__ import annotations

from agentloop.bounded_v2_llm import BoundedStrictV2Provider

ROLE_OUTPUT_BUDGETS = {
    "tester": 4_000,
    "critic": 500,
    "coder": 2_000,
}


class RoleBudgetV2Provider(BoundedStrictV2Provider):
    def generate(self, request):
        role = request.metadata.get("agent")
        budget = ROLE_OUTPUT_BUDGETS.get(role, request.max_output_tokens)
        bounded_request = request.model_copy(update={"max_output_tokens": budget})
        original_minimum = self.minimum_output_tokens
        self.minimum_output_tokens = budget
        try:
            return super().generate(bounded_request)
        finally:
            self.minimum_output_tokens = original_minimum
