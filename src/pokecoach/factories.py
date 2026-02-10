"""Shared builders for evidence and report claim placeholders."""

from __future__ import annotations

from pokecoach.constants import (
    PLACEHOLDER_MISTAKE_BETTER_LINE,
    PLACEHOLDER_MISTAKE_CONFIDENCE,
    PLACEHOLDER_MISTAKE_DESCRIPTION,
    PLACEHOLDER_MISTAKE_WHY,
    PLACEHOLDER_TURNING_POINT_CONFIDENCE,
    PLACEHOLDER_TURNING_POINT_IMPACT,
    PLACEHOLDER_TURNING_POINT_TITLE,
)
from pokecoach.schemas import EvidenceSpan, Mistake, TurningPoint


def build_evidence_span(line: int, text: str) -> EvidenceSpan:
    return EvidenceSpan(start_line=line, end_line=line, raw_lines=[text])


def build_placeholder_turning_point(event_line: int, event_text: str, seq: int) -> TurningPoint:
    return TurningPoint(
        title=PLACEHOLDER_TURNING_POINT_TITLE.format(seq=seq),
        impact=PLACEHOLDER_TURNING_POINT_IMPACT,
        confidence=PLACEHOLDER_TURNING_POINT_CONFIDENCE,
        depends_on_hidden_info=True,
        evidence=build_evidence_span(event_line, event_text),
    )


def build_placeholder_mistake(event_line: int, event_text: str) -> Mistake:
    return Mistake(
        description=PLACEHOLDER_MISTAKE_DESCRIPTION,
        why_it_matters=PLACEHOLDER_MISTAKE_WHY,
        better_line=PLACEHOLDER_MISTAKE_BETTER_LINE,
        confidence=PLACEHOLDER_MISTAKE_CONFIDENCE,
        depends_on_hidden_info=True,
        evidence=build_evidence_span(event_line, event_text),
    )
