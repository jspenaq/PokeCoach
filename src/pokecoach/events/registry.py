"""Registry of deterministic key event detectors."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from pokecoach.schemas import KeyEvent

EventDetector = Callable[[str, int, str], list[KeyEvent]]

SUPPORTER_KEYWORDS: tuple[str, ...] = (
    "Determinación de Lillie",
    "Órdenes de Jefes",
    "Ordenes de Jefes",
    "Liza",
    "Mirtilo",
    "Plan del Profesor Turo",
    "e-Nigma",
)

ATTACK_RE = re.compile(r"\binfligió\b.*\busando\b", re.IGNORECASE)
KO_RE = re.compile(r"quedó Fuera de Combate", re.IGNORECASE)
PRIZE_RE = re.compile(r"\btomó\b\s+(una|\d+)\s+cartas?\s+de\s+Premio", re.IGNORECASE)
CONCEDE_RE = re.compile(r"El rival se rindió", re.IGNORECASE)
STADIUM_IN_PLAY_RE = re.compile(r"puso en juego la carta de Estadio", re.IGNORECASE)
STADIUM_PLAY_RE = re.compile(
    r"\bjugó\b.*(Pueblo Altamía|Torre de Vigilancia del Equipo Rocket|Torre de Interferencia|Jaula de Combate)",
    re.IGNORECASE,
)


def _event(event_type: str, line: int, raw: str) -> KeyEvent:
    return KeyEvent(event_type=event_type, line=line, text=raw)


def detect_attack(text: str, line: int, raw: str) -> list[KeyEvent]:
    if ATTACK_RE.search(text):
        return [_event("ATTACK", line, raw)]
    return []


def detect_ko(text: str, line: int, raw: str) -> list[KeyEvent]:
    if KO_RE.search(text):
        return [_event("KO", line, raw)]
    return []


def detect_prize_taken(text: str, line: int, raw: str) -> list[KeyEvent]:
    if PRIZE_RE.search(text):
        return [_event("PRIZE_TAKEN", line, raw)]
    return []


def detect_concede(text: str, line: int, raw: str) -> list[KeyEvent]:
    if CONCEDE_RE.search(text):
        return [_event("CONCEDE", line, raw)]
    return []


def detect_stadium(text: str, line: int, raw: str) -> list[KeyEvent]:
    if STADIUM_IN_PLAY_RE.search(text) or STADIUM_PLAY_RE.search(text):
        return [_event("STADIUM", line, raw)]
    return []


def detect_supporter(text: str, line: int, raw: str) -> list[KeyEvent]:
    if "jugó" in text and any(keyword in text for keyword in SUPPORTER_KEYWORDS):
        return [_event("SUPPORTER", line, raw)]
    return []


EVENT_DETECTORS: Sequence[EventDetector] = (
    detect_attack,
    detect_ko,
    detect_prize_taken,
    detect_concede,
    detect_stadium,
    detect_supporter,
)
