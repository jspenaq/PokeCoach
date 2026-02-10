"""Deterministic tools for parser implementation."""

from __future__ import annotations

import re

from pokecoach.schemas import KeyEvent, KeyEventIndex, MatchStats, TurnSpan, TurnSummary

TURN_HEADER_RE = re.compile(r"^Turno de \[playerName\]\s*$")
ACTOR_PREFIX_RE = re.compile(r"^([A-Za-z0-9_\-]+)\s")

SUPPORTER_KEYWORDS = (
    "Determinación de Lillie",
    "Órdenes de Jefes",
    "Liza",
    "Mirtilo",
    "Plan del Profesor Turo",
    "e-Nigma",
)


def _infer_actor(lines: list[str]) -> str | None:
    for line in lines:
        text = line.strip()
        if not text or text.startswith("-") or text.startswith("•"):
            continue
        match = ACTOR_PREFIX_RE.match(text)
        if match:
            return match.group(1)
    return None


def index_turns(log_text: str) -> list[TurnSpan]:
    lines = log_text.splitlines()
    header_idxs = [i for i, line in enumerate(lines) if TURN_HEADER_RE.match(line.strip())]
    if not header_idxs:
        return []

    spans: list[TurnSpan] = []
    for turn_number, header_idx in enumerate(header_idxs, start=1):
        end_idx = header_idxs[turn_number] - 1 if turn_number < len(header_idxs) else len(lines) - 1
        block_lines = lines[header_idx : end_idx + 1]
        spans.append(
            TurnSpan(
                turn_number=turn_number,
                start_line=header_idx + 1,
                end_line=end_idx + 1,
                actor=_infer_actor(block_lines[1:]),
            )
        )
    return spans


def _iter_events(lines: list[str]) -> list[KeyEvent]:
    events: list[KeyEvent] = []
    for i, raw in enumerate(lines, start=1):
        text = raw.strip()
        if not text:
            continue

        if "quedó Fuera de Combate" in text:
            events.append(KeyEvent(event_type="KO", line=i, text=raw))

        if "tomó" in text and "carta" in text and "Premio" in text:
            events.append(KeyEvent(event_type="PRIZE_TAKEN", line=i, text=raw))

        if "El rival se rindió" in text:
            events.append(KeyEvent(event_type="CONCEDE", line=i, text=raw))

        if "infligió" in text and "usando" in text:
            events.append(KeyEvent(event_type="ATTACK", line=i, text=raw))

        if "puso en juego la carta de Estadio" in text:
            events.append(KeyEvent(event_type="STADIUM", line=i, text=raw))

        if "jugó" in text and any(keyword in text for keyword in SUPPORTER_KEYWORDS):
            events.append(KeyEvent(event_type="SUPPORTER", line=i, text=raw))

    return events


def find_key_events(log_text: str) -> KeyEventIndex:
    return KeyEventIndex(events=_iter_events(log_text.splitlines()))


def extract_turn_summary(turn_span: TurnSpan, log_text: str) -> TurnSummary:
    lines = log_text.splitlines()[turn_span.start_line - 1 : turn_span.end_line]
    bullets: list[str] = []

    for raw in lines:
        text = raw.strip()
        if "infligió" in text and "usando" in text:
            bullets.append("Attack resolved during this turn.")
        elif "quedó Fuera de Combate" in text:
            bullets.append("A knockout occurred during this turn.")
        elif "tomó" in text and "Premio" in text:
            bullets.append("A prize card was taken.")
        elif "jugó" in text and any(keyword in text for keyword in SUPPORTER_KEYWORDS):
            bullets.append("A supporter was played.")

    bullets = list(dict.fromkeys(bullets))[:4]
    if not bullets:
        bullets = ["Turn contained setup and sequencing actions."]

    return TurnSummary(turn_number=turn_span.turn_number, bullets=bullets, evidence=[])


def compute_basic_stats(log_text: str) -> MatchStats:
    lines = log_text.splitlines()

    players: list[str] = []
    for raw in lines:
        match = re.match(r"^([A-Za-z0-9_\-]+) robó 7 cartas de la mano inicial\.", raw.strip())
        if match and match.group(1) not in players:
            players.append(match.group(1))

    went_first_player: str | None = None
    mulligans_by_player: dict[str, int] = {}
    prizes_by_player: dict[str, int] = {}

    for raw in lines:
        text = raw.strip()

        first_match = re.match(r"^([A-Za-z0-9_\-]+) decidió empezar en (primer|segundo) lugar\.", text)
        if first_match:
            actor = first_match.group(1)
            choice = first_match.group(2)
            if choice == "primer":
                went_first_player = actor
            elif len(players) == 2:
                went_first_player = players[0] if players[1] == actor else players[1]

        one_mulligan = re.match(r"^([A-Za-z0-9_\-]+) declaró un mulligan\.", text)
        if one_mulligan:
            actor = one_mulligan.group(1)
            mulligans_by_player[actor] = mulligans_by_player.get(actor, 0) + 1

        many_mulligan = re.match(r"^([A-Za-z0-9_\-]+) declaró (\d+) mulligans\.", text)
        if many_mulligan:
            actor = many_mulligan.group(1)
            mulligans_by_player[actor] = mulligans_by_player.get(actor, 0) + int(many_mulligan.group(2))

        prize_match = re.match(r"^([A-Za-z0-9_\-]+) tomó (una|\d+) cartas? de Premio\.", text)
        if prize_match:
            actor = prize_match.group(1)
            count_text = prize_match.group(2)
            count = 1 if count_text == "una" else int(count_text)
            prizes_by_player[actor] = prizes_by_player.get(actor, 0) + count

    return MatchStats(
        went_first_player=went_first_player,
        mulligans_by_player=mulligans_by_player,
        observable_prizes_taken_by_player=prizes_by_player,
    )
