"""Deterministic tool interfaces for parser implementation."""

from __future__ import annotations

import re

from pokecoach.schemas import TurnSpan

TURN_HEADER_RE = re.compile(r"^Turno de \[playerName\]\s*$")
ACTOR_PREFIX_RE = re.compile(r"^([A-Za-z0-9_\-]+)\s")


def _infer_actor(lines: list[str]) -> str | None:
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if text.startswith("-") or text.startswith("•"):
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
        start_idx = header_idx
        end_idx = header_idxs[turn_number] - 1 if turn_number < len(header_idxs) else len(lines) - 1
        block_lines = lines[start_idx : end_idx + 1]
        spans.append(
            TurnSpan(
                turn_number=turn_number,
                start_line=start_idx + 1,
                end_line=end_idx + 1,
                actor=_infer_actor(block_lines[1:]),
            )
        )
    return spans


def find_key_events(log_text: str) -> dict[str, list[dict[str, str | int]]]:
    raise NotImplementedError


def extract_turn_summary(turn_span: TurnSpan, log_text: str) -> dict[str, object]:
    raise NotImplementedError


def compute_basic_stats(log_text: str) -> dict[str, object]:
    raise NotImplementedError
