from pathlib import Path

from pokecoach.tools import extract_play_bundles


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
