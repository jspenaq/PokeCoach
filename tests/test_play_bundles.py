from collections import Counter
from pathlib import Path

from pokecoach.tools import extract_play_bundles


def test_extract_play_bundles_log7_consolidates_turn_windows_3_to_6() -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt").read_text(encoding="utf-8")
    bundles = extract_play_bundles(log_text)

    window_counts = Counter(
        (bundle.turn_number, bundle.actor, bundle.window.start_line, bundle.window.end_line) for bundle in bundles
    )

    assert window_counts[(3, "Kami-Yan", 48, 92)] == 1
    assert window_counts[(4, "SpicyTaco30", 93, 130)] == 1
    assert window_counts[(5, "Kami-Yan", 131, 161)] == 1
    assert window_counts[(6, "SpicyTaco30", 162, 215)] == 1


def test_extract_play_bundles_log7_includes_gust_to_fezandipiti_ko_with_two_prizes() -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt").read_text(encoding="utf-8")
    bundles = extract_play_bundles(log_text)

    target_bundle = next(
        (
            bundle
            for bundle in bundles
            if bundle.gust_event is not None
            and "Órdenes de Jefes" in bundle.gust_event.text
            and any("Fezandipiti ex" in event.text for event in bundle.ko_events)
            and any("tomó 2 cartas de Premio" in event.text for event in bundle.prize_events)
        ),
        None,
    )

    assert target_bundle is not None


def test_extract_play_bundles_log7_includes_colagrito_ko_latias_with_two_prizes() -> None:
    log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt").read_text(encoding="utf-8")
    bundles = extract_play_bundles(log_text)

    target_bundle = next(
        (
            bundle
            for bundle in bundles
            if bundle.action_event is not None
            and "Colagrito" in bundle.action_event.text
            and any("Latias ex" in event.text for event in bundle.ko_events)
            and any("tomó 2 cartas de Premio" in event.text for event in bundle.prize_events)
        ),
        None,
    )

    assert target_bundle is not None
