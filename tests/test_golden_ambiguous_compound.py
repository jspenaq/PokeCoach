from pathlib import Path

from pokecoach.tools import find_key_events, index_turns

FIXTURES_DIR = Path("tests/golden/fixtures")


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_golden_ambiguous_turn_headers_and_interturn_blocks() -> None:
    log_text = _read_fixture("ambiguous_turns_interturn_block.txt")

    turns = index_turns(log_text)
    events = find_key_events(log_text).events

    assert len(turns) == 2
    assert turns[0].actor is None
    assert turns[1].actor == "Kami-Yan"
    assert turns[0].end_line == 4

    event_types = [event.event_type for event in events]
    assert "SUPPORTER" in event_types
    assert "ATTACK" in event_types
    assert "KO" in event_types
    assert "PRIZE_TAKEN" in event_types


def test_golden_compound_single_line_extracts_expected_event_bundle() -> None:
    log_text = _read_fixture("compound_single_line_events.txt")

    events = find_key_events(log_text).events
    by_line: dict[int, list[str]] = {}
    for event in events:
        by_line.setdefault(event.line, []).append(event.event_type)

    assert by_line[2] == ["STADIUM"]
    assert by_line[3] == ["SUPPORTER"]
    assert by_line[4] == ["ATTACK", "KO", "PRIZE_TAKEN"]
    assert by_line[5] == ["CONCEDE"]
