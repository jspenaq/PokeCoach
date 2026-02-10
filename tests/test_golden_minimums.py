import json
from pathlib import Path

import pytest

from pokecoach.tools import find_key_events, index_turns

EXPECTED_MINIMUMS_PATH = Path("tests/golden/expected_minimums.json")
LOGS_DIR = Path("logs_prueba")


with EXPECTED_MINIMUMS_PATH.open(encoding="utf-8") as fh:
    EXPECTED_MINIMUMS: dict[str, dict[str, int | bool]] = json.load(fh)


@pytest.mark.parametrize("log_name", sorted(EXPECTED_MINIMUMS))
def test_sample_logs_meet_minimum_expectations(log_name: str) -> None:
    expectations = EXPECTED_MINIMUMS[log_name]
    log_path = LOGS_DIR / log_name

    assert log_path.exists(), f"Sample log not found: {log_path}"

    log_text = log_path.read_text(encoding="utf-8")
    turns = index_turns(log_text)
    events = find_key_events(log_text).events

    attack_count = sum(1 for event in events if event.event_type == "ATTACK")
    ko_count = sum(1 for event in events if event.event_type == "KO")
    has_concede = any(event.event_type == "CONCEDE" for event in events)

    assert len(turns) >= int(expectations["min_turns"]), (
        f"{log_name}: expected at least {expectations['min_turns']} turns, got {len(turns)}"
    )
    assert attack_count >= int(expectations["min_attacks"]), (
        f"{log_name}: expected at least {expectations['min_attacks']} ATTACK events, got {attack_count}"
    )
    assert ko_count >= int(expectations["min_kos"]), (
        f"{log_name}: expected at least {expectations['min_kos']} KO events, got {ko_count}"
    )
    assert has_concede is bool(expectations["has_concede"]), (
        f"{log_name}: expected has_concede={expectations['has_concede']}, got {has_concede}"
    )
