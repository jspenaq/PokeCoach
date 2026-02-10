import re
from pathlib import Path

import pytest

from pokecoach import report as report_module
from pokecoach.report import generate_post_game_report
from pokecoach.tools import extract_turn_summary, index_turns


def test_extract_turn_summary_returns_bullets() -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish.txt")
    content = path.read_text(encoding="utf-8")
    turns = index_turns(content)

    summary = extract_turn_summary(turns[0], content)
    assert summary.turn_number == 1
    assert summary.bullets


def test_generate_post_game_report_contract() -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt")
    content = path.read_text(encoding="utf-8")

    report = generate_post_game_report(content)

    assert 5 <= len(report.summary) <= 8
    assert 2 <= len(report.turning_points) <= 4
    assert 3 <= len(report.mistakes) <= 6
    assert 3 <= len(report.next_actions) <= 5
    assert all(tp.evidence.raw_lines for tp in report.turning_points)
    assert all(ms.evidence.raw_lines for ms in report.mistakes)


def test_generate_post_game_report_uses_deterministic_fallback_when_llm_unavailable(monkeypatch) -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt")
    content = path.read_text(encoding="utf-8")

    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)
    report = generate_post_game_report(content)

    assert report.summary
    assert report.next_actions
    assert all(tp.evidence.raw_lines for tp in report.turning_points)
    assert all(ms.evidence.raw_lines for ms in report.mistakes)


@pytest.mark.parametrize(
    "fixture_path",
    [
        Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt"),
        Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_2.txt"),
    ],
)
def test_match_facts_and_summary_have_zero_discrepancies_for_deterministic_fixtures(
    monkeypatch, fixture_path: Path
) -> None:
    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)
    report = generate_post_game_report(fixture_path.read_text(encoding="utf-8"))

    first_turn_line = next((item for item in report.summary if item.endswith("took the first turn.")), None)
    if report.match_facts.went_first_player:
        assert first_turn_line is not None
        assert first_turn_line.startswith(report.match_facts.went_first_player)
    else:
        assert first_turn_line is None

    summary_ko_line = next(item for item in report.summary if item.endswith("knockout events."))
    summary_prize_line = next(item for item in report.summary if item.endswith("observable prize cards taken."))
    summary_turns_line = next(item for item in report.summary if item.endswith("turns in the log."))

    summary_ko_match = re.search(r"\d+", summary_ko_line)
    summary_prize_match = re.search(r"\d+", summary_prize_line)
    summary_turns_match = re.search(r"\d+", summary_turns_line)

    assert summary_ko_match is not None
    assert summary_prize_match is not None
    assert summary_turns_match is not None

    summary_ko_count = int(summary_ko_match.group())
    summary_prize_count = int(summary_prize_match.group())
    summary_turns_count = int(summary_turns_match.group())

    assert summary_ko_count == sum(report.match_facts.kos_by_player.values())
    assert summary_prize_count == sum(report.match_facts.observable_prizes_taken_by_player.values())
    assert summary_turns_count == report.match_facts.turns_count
