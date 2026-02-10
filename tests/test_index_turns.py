from pathlib import Path

from pokecoach.tools import index_turns


def _log_paths() -> list[Path]:
    base = Path("logs_prueba")
    return sorted(base.glob("battle_logs_9_feb_2026_spanish*.txt"))


def test_index_turns_parses_all_sample_logs() -> None:
    paths = _log_paths()
    assert len(paths) >= 5

    for path in paths:
        log_text = path.read_text(encoding="utf-8")
        spans = index_turns(log_text)

        assert spans, f"No turn spans parsed for {path.name}"
        assert all(span.start_line <= span.end_line for span in spans)
        assert all(spans[i].end_line < spans[i + 1].start_line for i in range(len(spans) - 1))


def test_index_turns_infers_actor_when_available() -> None:
    sample = """Preparación
Turno de [playerName]
Kami-Yan robó una carta.
Kami-Yan terminó su turno.

Turno de [playerName]
Rebokee robó una carta.
"""

    spans = index_turns(sample)
    assert len(spans) == 2
    assert spans[0].actor == "Kami-Yan"
    assert spans[1].actor == "Rebokee"
