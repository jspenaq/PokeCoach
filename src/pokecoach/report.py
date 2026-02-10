"""Post-game report assembly (initial MVP pipeline)."""

from __future__ import annotations

from pokecoach.constants import (
    DEFAULT_NEXT_ACTIONS,
    DEFAULT_UNKNOWNS,
    FALLBACK_SUMMARY_ITEMS,
    MISTAKE_EVENT_BETTER_LINE,
    MISTAKE_EVENT_CONFIDENCE,
    MISTAKE_EVENT_DESCRIPTION,
    MISTAKE_EVENT_WHY,
    MISTAKE_FALLBACK_BETTER_LINE,
    MISTAKE_FALLBACK_CONFIDENCE,
    MISTAKE_FALLBACK_DESCRIPTION,
    MISTAKE_FALLBACK_WHY,
    MISTAKES_MAX_ITEMS,
    MISTAKES_MIN_ITEMS,
    SUMMARY_MAX_ITEMS,
    TURNING_POINT_ATTACK_CONFIDENCE,
    TURNING_POINT_EVENT_CONFIDENCE,
    TURNING_POINT_EVENT_IMPACT,
    TURNING_POINT_FALLBACK_CONFIDENCE,
    TURNING_POINT_FALLBACK_IMPACT,
    TURNING_POINT_FALLBACK_TITLE,
    TURNING_POINTS_MAX_ITEMS,
    TURNING_POINTS_MIN_ITEMS,
    UNKNOWN_INFERRED_TURN_ACTORS,
)
from pokecoach.factories import build_evidence_span
from pokecoach.guardrails import apply_report_guardrails
from pokecoach.llm_provider import maybe_generate_guidance
from pokecoach.schemas import Mistake, PostGameReport, TurningPoint
from pokecoach.tools import compute_basic_stats, find_key_events, index_turns


def _summary_from_context(log_text: str) -> list[str]:
    stats = compute_basic_stats(log_text)
    events = find_key_events(log_text).events

    summary: list[str] = []
    if stats.went_first_player:
        summary.append(f"{stats.went_first_player} took the first turn.")

    ko_count = sum(1 for event in events if event.event_type == "KO")
    prize_count = sum(1 for event in events if event.event_type == "PRIZE_TAKEN")
    attack_count = sum(1 for event in events if event.event_type == "ATTACK")

    summary.append(f"Observed {attack_count} attack events in the log.")
    summary.append(f"Observed {ko_count} knockout events.")
    summary.append(f"Observed {prize_count} prize-taking events.")
    summary.append("Momentum swings were driven by attack-to-KO sequences.")
    summary.append("Unknown hidden information may change optimal lines.")

    return summary[:SUMMARY_MAX_ITEMS]


def _build_turning_points(log_text: str) -> list[TurningPoint]:
    events = find_key_events(log_text).events
    priority = [event for event in events if event.event_type in {"KO", "PRIZE_TAKEN", "ATTACK"}]

    turning_points: list[TurningPoint] = []
    for event in priority[:TURNING_POINTS_MAX_ITEMS]:
        turning_points.append(
            TurningPoint(
                title=f"{event.event_type} swing",
                impact=TURNING_POINT_EVENT_IMPACT,
                confidence=(
                    TURNING_POINT_EVENT_CONFIDENCE if event.event_type != "ATTACK" else TURNING_POINT_ATTACK_CONFIDENCE
                ),
                depends_on_hidden_info=event.event_type == "ATTACK",
                evidence=build_evidence_span(event.line, event.text),
            )
        )

    while len(turning_points) < TURNING_POINTS_MIN_ITEMS:
        fallback = events[0] if events else None
        if fallback is None:
            break
        turning_points.append(
            TurningPoint(
                title=TURNING_POINT_FALLBACK_TITLE,
                impact=TURNING_POINT_FALLBACK_IMPACT,
                confidence=TURNING_POINT_FALLBACK_CONFIDENCE,
                depends_on_hidden_info=True,
                evidence=build_evidence_span(fallback.line, fallback.text),
            )
        )

    return turning_points[:TURNING_POINTS_MAX_ITEMS]


def _build_mistakes(log_text: str) -> list[Mistake]:
    events = find_key_events(log_text).events
    candidates = [event for event in events if event.event_type in {"ATTACK", "KO", "SUPPORTER"}]

    mistakes: list[Mistake] = []
    for event in candidates[:MISTAKES_MAX_ITEMS]:
        mistakes.append(
            Mistake(
                description=MISTAKE_EVENT_DESCRIPTION.format(event_type=event.event_type.lower()),
                why_it_matters=MISTAKE_EVENT_WHY,
                better_line=MISTAKE_EVENT_BETTER_LINE,
                confidence=MISTAKE_EVENT_CONFIDENCE,
                depends_on_hidden_info=event.event_type != "KO",
                evidence=build_evidence_span(event.line, event.text),
            )
        )

    while len(mistakes) < MISTAKES_MIN_ITEMS:
        fallback = events[0] if events else None
        if fallback is None:
            break
        mistakes.append(
            Mistake(
                description=MISTAKE_FALLBACK_DESCRIPTION,
                why_it_matters=MISTAKE_FALLBACK_WHY,
                better_line=MISTAKE_FALLBACK_BETTER_LINE,
                confidence=MISTAKE_FALLBACK_CONFIDENCE,
                depends_on_hidden_info=True,
                evidence=build_evidence_span(fallback.line, fallback.text),
            )
        )

    return mistakes[:MISTAKES_MAX_ITEMS]


def generate_post_game_report(log_text: str) -> PostGameReport:
    turns = index_turns(log_text)
    summary = _summary_from_context(log_text)

    if len(summary) < 5:
        summary.extend(FALLBACK_SUMMARY_ITEMS)

    unknowns = list(DEFAULT_UNKNOWNS)
    if turns and turns[0].actor is None:
        unknowns.append(UNKNOWN_INFERRED_TURN_ACTORS)

    next_actions = list(DEFAULT_NEXT_ACTIONS)

    turning_points, mistakes, unknowns = apply_report_guardrails(
        log_text=log_text,
        turning_points=_build_turning_points(log_text),
        mistakes=_build_mistakes(log_text),
        unknowns=unknowns,
        event_indexer=find_key_events,
    )

    llm_guidance = maybe_generate_guidance(
        log_text=log_text,
        fallback_summary=summary[:SUMMARY_MAX_ITEMS],
        fallback_next_actions=next_actions,
    )
    if llm_guidance is not None:
        summary = llm_guidance.summary
        next_actions = llm_guidance.next_actions

    return PostGameReport(
        summary=summary[:SUMMARY_MAX_ITEMS],
        turning_points=turning_points,
        mistakes=mistakes,
        unknowns=unknowns,
        next_actions=next_actions,
    )
