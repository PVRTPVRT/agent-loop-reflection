"""Robust response protocols for agent decisions."""

from __future__ import annotations

from agentloop.agents import APPROVED_MARKER
from agentloop.grounded_agents import GroundedCriticAgent


class ProtocolCriticAgent(GroundedCriticAgent):
    """Recognize approval only as the final non-empty response line."""

    @staticmethod
    def is_approved(verdict: str) -> bool:
        lines = [line.strip() for line in verdict.splitlines() if line.strip()]
        return bool(lines and lines[-1] == APPROVED_MARKER)
