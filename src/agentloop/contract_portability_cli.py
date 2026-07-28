"""Observable portability entry point using public task contracts."""

from __future__ import annotations

import sys

from agentloop import observable_portability_cli
from agentloop.contract_agents import ContractCriticAgent, ContractTesterAgent


def main(argv: list[str] | None = None) -> int:
    observable_portability_cli.GroundedTesterAgent = ContractTesterAgent
    observable_portability_cli.GroundedCriticAgent = ContractCriticAgent
    return observable_portability_cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
