from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from agentloop.contracts_v2 import ContractRegistryV2
from agentloop.evaluation_v2_models import EvaluationDataset
from agentloop.suite_validation import validate_suite

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "benchmarks/contracts/coding-v3-hard-matrix-contracts.json"
HIDDEN_PATH = ROOT / "benchmarks/datasets/coding-v3-hard-matrix.json"
ROUTING_PATH = ROOT / "benchmarks/routing/coding-v3-hard-matrix-routing.json"
TASK_IDS = (
    "ttl-lru-001",
    "frame-decoder-001",
    "idempotent-ledger-001",
)


def _contract_fingerprint(registry: ContractRegistryV2) -> str:
    canonical = json.dumps(
        registry.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def test_hard_matrix_assets_are_frozen_and_oracle_validated() -> None:
    hidden = EvaluationDataset.load(HIDDEN_PATH)
    routing = EvaluationDataset.load(ROUTING_PATH)
    contracts = ContractRegistryV2.load(CONTRACT_PATH)

    assert hidden.dataset_id == contracts.dataset_id == "coding-v3-hard-matrix"
    assert routing.dataset_id == "coding-v3-hard-matrix-routing"
    assert tuple(task.task_id for task in hidden.tasks) == TASK_IDS
    assert tuple(task.task_id for task in routing.tasks) == TASK_IDS
    assert tuple(contracts.contracts) == TASK_IDS

    assert hidden.fingerprint == "d386595324cd2945"
    assert routing.fingerprint == "c7c62825a0ab821a"
    assert _contract_fingerprint(contracts) == "6b706547c7e5507d"

    for task in (*hidden.tasks, *routing.tasks):
        validated = validate_suite(
            task.evaluation_suite,
            contracts.require(task.task_id),
        )
        assert validated is task.evaluation_suite


def test_hard_matrix_generated_assets_match_reviewed_sources() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/build_v0_3_hard_matrix.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
