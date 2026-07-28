"""Strict-schema entry point for the resilient portability benchmark."""

from __future__ import annotations

import sys

from agentloop import structured_portability_cli
from agentloop.strict_json_llm import StrictJSONOpenAIProvider


def main(argv: list[str] | None = None) -> int:
    structured_portability_cli.StructuredOpenAIProvider = StrictJSONOpenAIProvider
    return structured_portability_cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
