"""Post-game report assembly (initial MVP pipeline)."""

from __future__ import annotations

from pokecoach.guardrails import apply_report_guardrails
from pokecoach.schemas import EvidenceSpan, Mistake, PostGameReport, TurningPoint
from pokecoach.tools import compute_basic_stats, find_key_events, index_turns


def _make_evidence(line: int, text: str) -> EvidenceSpan:
    return EvidenceSpan(start_line=line, end_line=line, raw_lines=[text])


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

    return summary[:8]


def _build_turning_points(log_text: str) -> list[TurningPoint]:
    events = find_key_events(log_text).events
    priority = [event for event in events if event.event_type in {"KO", "PRIZE_TAKEN", "ATTACK"}]

    turning_points: list[TurningPoint] = []
    for event in priority[:4]:
        turning_points.append(
            TurningPoint(
                title=f"{event.event_type} swing",
                impact="This event changed tempo or prize pressure.",
                confidence=0.75 if event.event_type != "ATTACK" else 0.62,
                depends_on_hidden_info=event.event_type == "ATTACK",
                evidence=_make_evidence(event.line, event.text),
            )
        )

    while len(turning_points) < 2:
        fallback = events[0] if events else None
        if fallback is None:
            break
        turning_points.append(
            TurningPoint(
                title="Early tempo signal",
                impact="Early sequence likely shaped the game flow.",
                confidence=0.55,
                depends_on_hidden_info=True,
                evidence=_make_evidence(fallback.line, fallback.text),
            )
        )

    return turning_points[:4]


def _build_mistakes(log_text: str) -> list[Mistake]:
    events = find_key_events(log_text).events
    candidates = [event for event in events if event.event_type in {"ATTACK", "KO", "SUPPORTER"}]

    mistakes: list[Mistake] = []
    for event in candidates[:6]:
        mistakes.append(
            Mistake(
                description=f"Review decision around {event.event_type.lower()} event.",
                why_it_matters="This sequence affected board pressure and prize race.",
                better_line="Re-evaluate sequencing before committing major actions.",
                confidence=0.64,
                depends_on_hidden_info=event.event_type != "KO",
                evidence=_make_evidence(event.line, event.text),
            )
        )

    while len(mistakes) < 3:
        fallback = events[0] if events else None
        if fallback is None:
            break
        mistakes.append(
            Mistake(
                description="Review early setup sequencing.",
                why_it_matters="Early sequencing influences later tempo windows.",
                better_line="Run pre-attack sequencing checklist.",
                confidence=0.55,
                depends_on_hidden_info=True,
                evidence=_make_evidence(fallback.line, fallback.text),
            )
        )

    return mistakes[:6]


def generate_post_game_report(log_text: str) -> PostGameReport:
    turns = index_turns(log_text)
    summary = _summary_from_context(log_text)

    if len(summary) < 5:
        summary.extend(
            [
                "Opening turns established initial board state.",
                "Mid-game exchanges influenced tempo.",
                "Endgame lines depended on available resources.",
            ]
        )

    unknowns = [
        "Opponent hand information is incomplete.",
        "Prize card mapping is partially hidden unless revealed in the log.",
    ]
    if turns and turns[0].actor is None:
        unknowns.append("Some turn actors were inferred due to placeholder turn headers.")

    next_actions = [
        "Practice prize mapping before each high-impact attack.",
        "Review supporter sequencing on turns with tempo swings.",
        "Rehearse a pre-commit checklist for attack and retreat decisions.",
    ]

    turning_points, mistakes, unknowns = apply_report_guardrails(
        log_text=log_text,
        turning_points=_build_turning_points(log_text),
        mistakes=_build_mistakes(log_text),
        unknowns=unknowns,
        event_indexer=find_key_events,
    )

    return PostGameReport(
        summary=summary[:8],
        turning_points=turning_points,
        mistakes=mistakes,
        unknowns=unknowns,
        next_actions=next_actions,
    )
