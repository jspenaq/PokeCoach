"""Guardrail enforcement for post-game report claims."""

from __future__ import annotations

from collections.abc import Callable

from pokecoach.constants import (
    MIN_CONFIDENCE,
    MISTAKES_MAX_ITEMS,
    MISTAKES_MIN_ITEMS,
    TURNING_POINTS_MAX_ITEMS,
    TURNING_POINTS_MIN_ITEMS,
    UNKNOWN_LOW_CONF_MISTAKE,
    UNKNOWN_LOW_CONF_TURNING_POINT,
)
from pokecoach.factories import build_placeholder_mistake, build_placeholder_turning_point
from pokecoach.schemas import KeyEventIndex, Mistake, TurningPoint


def _has_non_empty_evidence(raw_lines: list[str] | None) -> bool:
    if not raw_lines:
        return False
    return any(line.strip() for line in raw_lines)


def _append_unknown_once(unknowns: list[str], seen: set[str], claim: str) -> None:
    if claim in seen:
        return
    unknowns.append(claim)
    seen.add(claim)


def apply_report_guardrails(
    log_text: str,
    turning_points: list[TurningPoint],
    mistakes: list[Mistake],
    unknowns: list[str],
    *,
    event_indexer: Callable[[str], KeyEventIndex],
) -> tuple[list[TurningPoint], list[Mistake], list[str]]:
    events = event_indexer(log_text).events
    normalized_unknowns = list(dict.fromkeys(unknowns))
    unknown_seen = set(normalized_unknowns)

    valid_turning_points: list[TurningPoint] = []
    for item in turning_points:
        if not _has_non_empty_evidence(getattr(item.evidence, "raw_lines", None)):
            continue
        if item.confidence < MIN_CONFIDENCE:
            _append_unknown_once(
                normalized_unknowns,
                unknown_seen,
                UNKNOWN_LOW_CONF_TURNING_POINT.format(title=item.title),
            )
            continue
        valid_turning_points.append(item)

    valid_mistakes: list[Mistake] = []
    for item in mistakes:
        if not _has_non_empty_evidence(getattr(item.evidence, "raw_lines", None)):
            continue
        if item.confidence < MIN_CONFIDENCE:
            _append_unknown_once(
                normalized_unknowns,
                unknown_seen,
                UNKNOWN_LOW_CONF_MISTAKE.format(description=item.description),
            )
            continue
        valid_mistakes.append(item)

    fallback_events = [(event.line, event.text) for event in events if event.text.strip()]
    if fallback_events:
        idx = 0
        while len(valid_turning_points) < TURNING_POINTS_MIN_ITEMS:
            line, text = fallback_events[idx % len(fallback_events)]
            valid_turning_points.append(build_placeholder_turning_point(line, text, len(valid_turning_points) + 1))
            idx += 1

        idx = 0
        while len(valid_mistakes) < MISTAKES_MIN_ITEMS:
            line, text = fallback_events[idx % len(fallback_events)]
            valid_mistakes.append(build_placeholder_mistake(line, text))
            idx += 1

    return (
        valid_turning_points[:TURNING_POINTS_MAX_ITEMS],
        valid_mistakes[:MISTAKES_MAX_ITEMS],
        normalized_unknowns,
    )
