import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATURAL_TRACE = (
    ROOT / "benchmarks/traces/adaptive-v0.3-hard-matrix-pilot/ttl-lru-001.json"
)
PROMPT_ONLY_TRACE = (
    ROOT
    / "benchmarks/traces/repair-replay-v0.3-exact-natural-prompt-only-failure"
    / "ttl-lru-001.json"
)
HISTORY_TRACE = (
    ROOT
    / "benchmarks/traces/repair-replay-v0.3-exact-natural-failure"
    / "ttl-lru-001.json"
)
RECORDED_CANDIDATE = (
    ROOT / "benchmarks/fixtures/ttl-lru-v0.3-natural-direct-failure.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_recorded_candidate_is_exactly_the_natural_direct_failure() -> None:
    natural = load_json(NATURAL_TRACE)
    candidate = RECORDED_CANDIDATE.read_text(encoding="utf-8")

    assert natural["path"] == "reflection"
    assert natural["result"]["success"] is False
    assert natural["direct_code"].rstrip() == candidate.rstrip()


def test_prompt_only_failure_and_history_success_share_the_same_candidate() -> None:
    candidate = RECORDED_CANDIDATE.read_text(encoding="utf-8").rstrip()
    prompt_only = load_json(PROMPT_ONLY_TRACE)
    with_history = load_json(HISTORY_TRACE)

    assert prompt_only["recorded_candidate"].rstrip() == candidate
    assert with_history["recorded_candidate"].rstrip() == candidate
    assert prompt_only["result"]["success"] is False
    assert with_history["result"]["success"] is True
    assert with_history["hidden_verification"]["success"] is True

    diagnoses = [
        event
        for event in with_history["workflow_result"]["events"]
        if event["event_type"] == "repair_diagnosed"
    ]
    assert [event["metadata"]["history_length"] for event in diagnoses] == [0, 2]
