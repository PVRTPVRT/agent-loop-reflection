"""Single supported V2 command dispatcher."""

from __future__ import annotations

import argparse

from agentloop import adaptive_v2_cli, direct_v2_cli, lean_reflection_v2_cli

COMMANDS = {
    "direct": direct_v2_cli.main,
    "reflection": lean_reflection_v2_cli.main,
    "adaptive": adaptive_v2_cli.main,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent Loop Reflection V2")
    parser.add_argument(
        "mode",
        choices=COMMANDS,
        help="Execution strategy.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args, remaining = parser.parse_known_args(argv)
    return COMMANDS[args.mode](remaining)


if __name__ == "__main__":
    raise SystemExit(main())
