"""Guardrail enforcement for post-game report claims."""

from __future__ import annotations

from collections.abc import Callable

from pokecoach.schemas import EvidenceSpan, KeyEventIndex, Mistake, TurningPoint


def _make_evidence(line: int, text: str) -> EvidenceSpan:
    return EvidenceSpan(start_line=line, end_line=line, raw_lines=[text])


def _has_non_empty_evidence(raw_lines: list[str] | None) -> bool:
    if not raw_lines:
        return False
    return any(line.strip() for line in raw_lines)


def _append_unknown_once(unknowns: list[str], seen: set[str], claim: str) -> None:
    if claim in seen:
        return
    unknowns.append(claim)
    seen.add(claim)


def _placeholder_turning_point(event_line: int, event_text: str, seq: int) -> TurningPoint:
    return TurningPoint(
        title=f"Evidence-backed tempo signal {seq}",
        impact="Observed event may have influenced tempo; verify board context.",
        confidence=0.55,
        depends_on_hidden_info=True,
        evidence=_make_evidence(event_line, event_text),
    )


def _placeholder_mistake(event_line: int, event_text: str) -> Mistake:
    return Mistake(
        description="Review sequencing around observed event.",
        why_it_matters="Observed sequence may have narrowed available lines.",
        better_line="Replay this turn and compare at least one alternative sequence.",
        confidence=0.55,
        depends_on_hidden_info=True,
        evidence=_make_evidence(event_line, event_text),
    )


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
        if item.confidence < 0.55:
            _append_unknown_once(
                normalized_unknowns,
                unknown_seen,
                f"Low-confidence turning point omitted: {item.title}",
            )
            continue
        valid_turning_points.append(item)

    valid_mistakes: list[Mistake] = []
    for item in mistakes:
        if not _has_non_empty_evidence(getattr(item.evidence, "raw_lines", None)):
            continue
        if item.confidence < 0.55:
            _append_unknown_once(
                normalized_unknowns,
                unknown_seen,
                f"Low-confidence mistake omitted: {item.description}",
            )
            continue
        valid_mistakes.append(item)

    fallback_events = [(event.line, event.text) for event in events if event.text.strip()]
    if fallback_events:
        idx = 0
        while len(valid_turning_points) < 2:
            line, text = fallback_events[idx % len(fallback_events)]
            valid_turning_points.append(_placeholder_turning_point(line, text, len(valid_turning_points) + 1))
            idx += 1

        idx = 0
        while len(valid_mistakes) < 3:
            line, text = fallback_events[idx % len(fallback_events)]
            valid_mistakes.append(_placeholder_mistake(line, text))
            idx += 1

    return valid_turning_points[:4], valid_mistakes[:6], normalized_unknowns
