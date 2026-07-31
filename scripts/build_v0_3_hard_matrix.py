"""Build the frozen v0.3 hard-task benchmark matrix from reviewed source assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SOURCES = (
    {
        "task_id": "ttl-lru-001",
        "contract": "benchmarks/contracts/coding-v2-repair-contracts.json",
        "hidden": "benchmarks/datasets/coding-v2-repair-pilot-r2.json",
        "routing": "benchmarks/routing/coding-v2-repair-routing.json",
    },
    {
        "task_id": "frame-decoder-001",
        "contract": "benchmarks/contracts/coding-v3-frame-decoder-contracts.json",
        "hidden": "benchmarks/datasets/coding-v3-frame-decoder-pilot.json",
        "routing": "benchmarks/routing/coding-v3-frame-decoder-routing.json",
    },
    {
        "task_id": "idempotent-ledger-001",
        "contract": "benchmarks/contracts/coding-v3-idempotent-ledger-contracts.json",
        "hidden": "benchmarks/datasets/coding-v3-idempotent-ledger-pilot.json",
        "routing": "benchmarks/routing/coding-v3-idempotent-ledger-routing.json",
    },
)

OUTPUTS = {
    "contracts": ROOT / "benchmarks/contracts/coding-v3-hard-matrix-contracts.json",
    "hidden": ROOT / "benchmarks/datasets/coding-v3-hard-matrix.json",
    "routing": ROOT / "benchmarks/routing/coding-v3-hard-matrix-routing.json",
}


def _load(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def _require_task(document: dict[str, Any], task_id: str) -> dict[str, Any]:
    matches = [task for task in document["tasks"] if task["task_id"] == task_id]
    if len(matches) != 1:
        raise ValueError(
            f"{document.get('dataset_id', '<unknown>')} must contain task "
            f"{task_id!r} exactly once"
        )
    return matches[0]


def build_documents() -> dict[str, dict[str, Any]]:
    contracts: dict[str, Any] = {}
    hidden_tasks: list[dict[str, Any]] = []
    routing_tasks: list[dict[str, Any]] = []

    for source in SOURCES:
        task_id = source["task_id"]
        contract_document = _load(source["contract"])
        if task_id not in contract_document["contracts"]:
            raise ValueError(f"{source['contract']} has no contract for {task_id!r}")
        if task_id in contracts:
            raise ValueError(f"duplicate task id in matrix: {task_id!r}")
        contracts[task_id] = contract_document["contracts"][task_id]
        hidden_tasks.append(_require_task(_load(source["hidden"]), task_id))
        routing_tasks.append(_require_task(_load(source["routing"]), task_id))

    return {
        "contracts": {
            "schema_version": "2.0",
            "dataset_id": "coding-v3-hard-matrix",
            "contracts": contracts,
        },
        "hidden": {
            "schema_version": "2.0",
            "dataset_id": "coding-v3-hard-matrix",
            "description": (
                "Frozen v0.3 hard-task matrix spanning cache timing, stream "
                "framing, and idempotent event processing."
            ),
            "tasks": hidden_tasks,
        },
        "routing": {
            "schema_version": "2.0",
            "dataset_id": "coding-v3-hard-matrix-routing",
            "description": (
                "Public routing suites for the frozen v0.3 hard-task matrix."
            ),
            "tasks": routing_tasks,
        },
    }


def _serialize(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if committed matrix assets differ from their reviewed sources.",
    )
    args = parser.parse_args(argv)

    documents = build_documents()
    stale: list[Path] = []
    for name, output_path in OUTPUTS.items():
        expected = _serialize(documents[name])
        if args.check:
            if not output_path.exists() or output_path.read_text(encoding="utf-8") != expected:
                stale.append(output_path)
            continue
        output_path.write_text(expected, encoding="utf-8", newline="\n")
        print(f"Wrote {output_path.relative_to(ROOT)}")

    if stale:
        for path in stale:
            print(f"STALE: {path.relative_to(ROOT)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
