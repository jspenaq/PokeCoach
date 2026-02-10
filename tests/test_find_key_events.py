from pathlib import Path

from pokecoach.tools import find_key_events


def _all_logs() -> list[Path]:
    return sorted(Path("logs_prueba").glob("battle_logs_ptcgl_spanish*.txt"))


def test_find_key_events_detects_core_event_types() -> None:
    event_types_found: set[str] = set()

    for path in _all_logs():
        content = path.read_text(encoding="utf-8")
        index = find_key_events(content)
        event_types_found.update(event.event_type for event in index.events)

    assert "KO" in event_types_found
    assert "PRIZE_TAKEN" in event_types_found
    assert "CONCEDE" in event_types_found
    assert "ATTACK" in event_types_found
    assert "STADIUM" in event_types_found
    assert "SUPPORTER" in event_types_found


def test_find_key_events_supports_multiple_events_from_same_line() -> None:
    log_text = (
        "Turno de [playerName]\n"
        "Kami-Yan infligió 180 puntos de daño usando Comodín Nocturno contra X. "
        "¡X quedó Fuera de Combate! Kami-Yan tomó una carta de Premio.\n"
    )

    index = find_key_events(log_text)
    types = [event.event_type for event in index.events]

    assert "ATTACK" in types
    assert "KO" in types
    assert "PRIZE_TAKEN" in types


def test_find_key_events_detects_supporter_with_card_ids() -> None:
    log_text = "Kami-Yan jugó (me1_119) Determinación de Lillie.\n"
    index = find_key_events(log_text)

    assert any(event.event_type == "SUPPORTER" for event in index.events)


def test_find_key_events_detects_stadium_from_play_line() -> None:
    log_text = "Kami-Yan jugó Pueblo Altamía.\n"
    index = find_key_events(log_text)

    assert any(event.event_type == "STADIUM" for event in index.events)
