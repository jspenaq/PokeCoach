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
    assert all(not line.startswith("Turn window ") for bundle in bundles for line in bundle.window.raw_lines)


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
    assert "Kami-Yan jugó (me1_114) Órdenes de Jefes." in target_bundle.window.raw_lines
    assert (
        "El (me2_128) Mega-Lopunny ex de Kami-Yan infligió 230 puntos de daño "
        "usando Impulso Vendaval contra el (me2-5_142) Fezandipiti ex de SpicyTaco30."
    ) in target_bundle.window.raw_lines
    assert "¡El (me2-5_142) Fezandipiti ex de SpicyTaco30 quedó Fuera de Combate!" in target_bundle.window.raw_lines
    assert "Kami-Yan tomó 2 cartas de Premio." in target_bundle.window.raw_lines


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
    assert "El (sv4_86) Colagrito de SpicyTaco30 usó Grito Rugiente." in target_bundle.window.raw_lines
    assert "¡El (sv8_220) Latias ex de Kami-Yan quedó Fuera de Combate!" in target_bundle.window.raw_lines
    assert "SpicyTaco30 tomó 2 cartas de Premio." in target_bundle.window.raw_lines
