import re
from pathlib import Path

import pytest

from pokecoach import report as report_module
from pokecoach.llm_provider import LLMReportGuidance
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


def test_summary_integrity_rewrites_unverifiable_ko_actor_claim_for_log7(monkeypatch) -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt")
    content = path.read_text(encoding="utf-8")
    monkeypatch.setattr(
        report_module,
        "maybe_generate_guidance",
        lambda **_kwargs: LLMReportGuidance(
            summary=[
                "Mega-Lopunny ex KO Latias ex.",
                "Tempo shifted after that exchange.",
                "Prize pressure increased.",
                "Unknown hidden info remains relevant.",
                "Late game sequencing was decisive.",
            ],
            next_actions=[
                "Review sequencing.",
                "Track prizes.",
                "Plan retreat lines.",
            ],
        ),
    )

    report = generate_post_game_report(content)

    assert all("lopunny ex ko latias ex" not in item.lower() for item in report.summary)
    assert "Observed knockout: Latias ex was knocked out." in report.summary


def test_summary_integrity_moves_unverifiable_ko_claim_to_unknowns(monkeypatch) -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt")
    log_text = path.read_text(encoding="utf-8")
    monkeypatch.setattr(
        report_module,
        "maybe_generate_guidance",
        lambda **_kwargs: LLMReportGuidance(
            summary=[
                "Mega-Lopunny ex KO MissingTarget ex.",
                "Tempo was contested.",
                "Prize race mattered.",
                "Opening setup was uneven.",
                "Unknown hand info affected options.",
            ],
            next_actions=[
                "Review opening hands.",
                "Track known resources.",
                "Practice sequencing.",
            ],
        ),
    )

    report = generate_post_game_report(log_text)

    assert all("mega-lopunny ex ko missingtarget ex" not in item.lower() for item in report.summary)
    assert any(
        item.startswith("Unverifiable KO summary claim omitted: Mega-Lopunny ex KO MissingTarget ex.")
        for item in report.unknowns
    )


def test_turning_points_rank_by_impact_score_not_order(monkeypatch) -> None:
    log_text = "\n".join(
        [
            "Turno de [playerName]",
            "Alice usó Golpe Ligero.",
            "¡El (sv1_25) Pikachu de Bob quedó Fuera de Combate!",
            "Alice tomó una carta de Premio.",
            "Turno de [playerName]",
            "Bob usó Ataque Final.",
            "¡El (sv8_220) Latias ex de Alice quedó Fuera de Combate!",
            "Bob tomó 2 cartas de Premio.",
        ]
    )
    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)

    report = generate_post_game_report(log_text)

    assert "Latias ex" in " ".join(report.turning_points[0].evidence.raw_lines)
    assert "tomó 2 cartas de Premio." in " ".join(report.turning_points[0].evidence.raw_lines)


def test_turning_points_log7_include_required_two_prize_ko_targets(monkeypatch) -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt").read_text(encoding="utf-8")
    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)

    report = generate_post_game_report(log_text)

    assert any(
        "Latias ex" in " ".join(tp.evidence.raw_lines) and "tomó 2 cartas de Premio." in " ".join(tp.evidence.raw_lines)
        for tp in report.turning_points
    )
    assert any(
        "Fezandipiti ex" in " ".join(tp.evidence.raw_lines)
        and "tomó 2 cartas de Premio." in " ".join(tp.evidence.raw_lines)
        for tp in report.turning_points
    )


def test_turning_points_include_endgame_concede_when_present(monkeypatch) -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt").read_text(encoding="utf-8")
    monkeypatch.setattr(report_module, "maybe_generate_guidance", lambda **_kwargs: None)

    report = generate_post_game_report(log_text)

    assert any(tp.title == "Concede closes endgame" for tp in report.turning_points)
