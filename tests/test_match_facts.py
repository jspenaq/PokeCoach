from pathlib import Path

from pokecoach.tools import extract_match_facts, index_turns


def test_match_facts_extracts_winner_and_concede() -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_1.txt")
    facts = extract_match_facts(path.read_text(encoding="utf-8"))

    assert facts.concede is True
    assert facts.winner == "Kami-Yan"


def test_match_facts_counts_prizes() -> None:
    log_text = (
        "A robó 7 cartas de la mano inicial.\n"
        "B robó 7 cartas de la mano inicial.\n"
        "A tomó una carta de Premio.\n"
        "A tomó 2 cartas de Premio.\n"
        "B tomó 3 cartas de Premio.\n"
    )

    facts = extract_match_facts(log_text)
    assert facts.observable_prizes_taken_by_player == {"A": 3, "B": 3}


def test_match_facts_turn_count() -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_2.txt")
    log_text = path.read_text(encoding="utf-8")

    facts = extract_match_facts(log_text)
    assert facts.turns_count == len(index_turns(log_text))


def test_match_facts_log7_ko_keys_are_limited_to_players_and_unknown() -> None:
    path = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt")
    facts = extract_match_facts(path.read_text(encoding="utf-8"))

    assert set(facts.kos_by_player) <= {"Kami-Yan", "SpicyTaco30", "unknown"}
