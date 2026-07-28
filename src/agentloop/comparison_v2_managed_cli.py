"""V2 comparison entry point using guaranteed Docker cleanup."""

from __future__ import annotations

import sys

from agentloop import comparison_v2_cli
from agentloop.managed_sandbox_v2 import ManagedDockerSandboxV2


def main(argv: list[str] | None = None) -> int:
    comparison_v2_cli.DockerSandboxV2 = ManagedDockerSandboxV2
    return comparison_v2_cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
