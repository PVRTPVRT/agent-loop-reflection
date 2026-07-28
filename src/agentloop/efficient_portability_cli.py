"""Observable portability entry point with the robust Critic protocol."""

from __future__ import annotations

import sys

from agentloop import observable_portability_cli
from agentloop.protocol_agents import ProtocolCriticAgent


def main(argv: list[str] | None = None) -> int:
    observable_portability_cli.GroundedCriticAgent = ProtocolCriticAgent
    return observable_portability_cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
