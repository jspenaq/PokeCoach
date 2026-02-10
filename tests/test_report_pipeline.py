from pathlib import Path

from pokecoach import report as report_module
from pokecoach.report import generate_post_game_report
from pokecoach.tools import extract_turn_summary, index_turns


def test_extract_turn_summary_returns_bullets() -> None:
    path = Path("logs_prueba/battle_logs_9_feb_2026_spanish.txt")
    content = path.read_text(encoding="utf-8")
    turns = index_turns(content)

    summary = extract_turn_summary(turns[0], content)
    assert summary.turn_number == 1
    assert summary.bullets


def test_generate_post_game_report_contract() -> None:
    path = Path("logs_prueba/battle_logs_9_feb_2026_spanish_con_ids_1.txt")
    content = path.read_text(encoding="utf-8")

    report = generate_post_game_report(content)

    assert 5 <= len(report.summary) <= 8
    assert 2 <= len(report.turning_points) <= 4
    assert 3 <= len(report.mistakes) <= 6
    assert 3 <= len(report.next_actions) <= 5
    assert all(tp.evidence.raw_lines for tp in report.turning_points)
    assert all(ms.evidence.raw_lines for ms in report.mistakes)


def test_generate_post_game_report_uses_deterministic_fallback_when_llm_unavailable(monkeypatch) -> None:
    path = Path("logs_prueba/battle_logs_9_feb_2026_spanish_con_ids_1.txt")
    content = path.read_text(encoding="utf-8")

    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)
    report = generate_post_game_report(content)

    assert report.summary
    assert report.next_actions
    assert all(tp.evidence.raw_lines for tp in report.turning_points)
    assert all(ms.evidence.raw_lines for ms in report.mistakes)
