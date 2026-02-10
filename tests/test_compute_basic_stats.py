from pathlib import Path

from pokecoach.tools import compute_basic_stats


def test_compute_basic_stats_from_sample_log() -> None:
    path = Path("logs_prueba/battle_logs_9_feb_2026_spanish.txt")
    stats = compute_basic_stats(path.read_text(encoding="utf-8"))

    assert stats.went_first_player == "XueDii"
    assert stats.mulligans_by_player.get("Kami-Yan") == 3
    assert stats.observable_prizes_taken_by_player.get("Kami-Yan", 0) >= 1


def test_compute_basic_stats_handles_second_player_choice() -> None:
    log_text = (
        "A robó 7 cartas de la mano inicial.\n"
        "B robó 7 cartas de la mano inicial.\n"
        "A decidió empezar en segundo lugar.\n"
    )

    stats = compute_basic_stats(log_text)
    assert stats.went_first_player == "B"
