"""Post-game report assembly (initial MVP pipeline)."""

from __future__ import annotations

import re

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
from pokecoach.schemas import EvidenceSpan, KeyEvent, MatchFacts, Mistake, PostGameReport, TurningPoint
from pokecoach.summary_integrity import apply_summary_claim_integrity
from pokecoach.tools import extract_match_facts, extract_play_bundles, find_key_events, index_turns

IMPACT_KO_BASE = 100
IMPACT_TWO_PRIZE_SWING_BONUS = 35
IMPACT_HIGH_IMPACT_TARGET_BONUS = 20
IMPACT_CONCEDE_ENDGAME_SCORE = 130
PRIZE_COUNT_RE = re.compile(r"tomó (una|\d+) cartas? de Premio\.", re.IGNORECASE)
HIGH_IMPACT_TARGET_RE = re.compile(r"\bex\b", re.IGNORECASE)
KO_TARGET_RE = re.compile(
    r"^\s*[¡!]?\s*El\s+\([^)]+\)\s+(.+?)\s+de\s+[A-Za-z0-9_\-]+\s+quedó Fuera de Combate[.!¡!]*\s*$"
)


def _bundle_evidence(bundle_events: list[tuple[int, str]]) -> EvidenceSpan:
    start_line = min(line for line, _ in bundle_events)
    end_line = max(line for line, _ in bundle_events)
    return EvidenceSpan(start_line=start_line, end_line=end_line, raw_lines=[text for _, text in bundle_events])


def _extract_prize_count(prize_text: str) -> int:
    match = PRIZE_COUNT_RE.search(prize_text.strip())
    if not match:
        return 0
    count_text = match.group(1).lower()
    if count_text == "una":
        return 1
    return int(count_text)


def _extract_ko_target(ko_text: str) -> str:
    match = KO_TARGET_RE.match(ko_text.strip())
    if not match:
        return "Unknown target"
    return match.group(1)


def _build_bundle_turning_point(bundle) -> tuple[int, int, TurningPoint] | None:
    if not bundle.ko_events:
        return None

    bundle_events = []
    if bundle.gust_event is not None:
        bundle_events.append((bundle.gust_event.line, bundle.gust_event.text))
    if bundle.action_event is not None:
        bundle_events.append((bundle.action_event.line, bundle.action_event.text))
    bundle_events.extend((event.line, event.text) for event in bundle.ko_events)
    bundle_events.extend((event.line, event.text) for event in bundle.prize_events)
    if not bundle_events:
        return None

    score = IMPACT_KO_BASE
    total_prizes = sum(_extract_prize_count(event.text) for event in bundle.prize_events)
    has_two_prize_swing = total_prizes >= 2
    has_high_impact_target = any(HIGH_IMPACT_TARGET_RE.search(event.text) for event in bundle.ko_events)

    if has_two_prize_swing:
        score += IMPACT_TWO_PRIZE_SWING_BONUS
    if has_high_impact_target:
        score += IMPACT_HIGH_IMPACT_TARGET_BONUS

    primary_target = _extract_ko_target(bundle.ko_events[0].text)
    impact_parts = [f"Impact score {score}: KO base (+{IMPACT_KO_BASE})."]
    if has_two_prize_swing:
        impact_parts.append(f"2-prize swing bonus (+{IMPACT_TWO_PRIZE_SWING_BONUS}).")
    if has_high_impact_target:
        impact_parts.append(f"High-impact target bonus (+{IMPACT_HIGH_IMPACT_TARGET_BONUS}).")

    return (
        score,
        min(line for line, _ in bundle_events),
        TurningPoint(
            title=f"KO swing on {primary_target}",
            impact=" ".join(impact_parts),
            confidence=TURNING_POINT_EVENT_CONFIDENCE,
            depends_on_hidden_info=False,
            evidence=_bundle_evidence(bundle_events),
        ),
    )


def _build_concede_turning_point(event: KeyEvent) -> tuple[int, int, TurningPoint]:
    return (
        IMPACT_CONCEDE_ENDGAME_SCORE,
        event.line,
        TurningPoint(
            title="Concede closes endgame",
            impact=f"Impact score {IMPACT_CONCEDE_ENDGAME_SCORE}: concession ended the game state.",
            confidence=TURNING_POINT_EVENT_CONFIDENCE,
            depends_on_hidden_info=False,
            evidence=build_evidence_span(event.line, event.text),
        ),
    )


def _build_event_turning_point(event: KeyEvent) -> tuple[int, int, TurningPoint]:
    score = 10
    if event.event_type == "KO":
        score = IMPACT_KO_BASE
    elif event.event_type == "PRIZE_TAKEN":
        prizes = _extract_prize_count(event.text)
        score = 30 + (IMPACT_TWO_PRIZE_SWING_BONUS if prizes >= 2 else 0)
    elif event.event_type == "ATTACK":
        score = 10

    confidence = TURNING_POINT_EVENT_CONFIDENCE if event.event_type != "ATTACK" else TURNING_POINT_ATTACK_CONFIDENCE
    return (
        score,
        event.line,
        TurningPoint(
            title=f"{event.event_type} swing",
            impact=f"Impact score {score}: deterministic event impact weight.",
            confidence=confidence,
            depends_on_hidden_info=event.event_type == "ATTACK",
            evidence=build_evidence_span(event.line, event.text),
        ),
    )


def _summary_from_context(log_text: str, match_facts: MatchFacts) -> list[str]:
    events = find_key_events(log_text).events

    summary: list[str] = []
    if match_facts.went_first_player:
        summary.append(f"{match_facts.went_first_player} took the first turn.")

    ko_count = sum(match_facts.kos_by_player.values())
    prize_count = sum(match_facts.observable_prizes_taken_by_player.values())
    attack_count = sum(1 for event in events if event.event_type == "ATTACK")

    summary.append(f"Observed {attack_count} attack events in the log.")
    summary.append(f"Observed {ko_count} knockout events.")
    summary.append(f"Observed {prize_count} observable prize cards taken.")
    summary.append(f"Observed {match_facts.turns_count} turns in the log.")
    summary.append("Momentum swings were driven by attack-to-KO sequences.")
    summary.append("Unknown hidden information may change optimal lines.")

    return summary[:SUMMARY_MAX_ITEMS]


def _build_turning_points(log_text: str) -> list[TurningPoint]:
    events = find_key_events(log_text).events
    scored_candidates: list[tuple[int, int, TurningPoint]] = []

    for bundle in extract_play_bundles(log_text):
        candidate = _build_bundle_turning_point(bundle)
        if candidate is not None:
            scored_candidates.append(candidate)

    concede_event = next((event for event in events if event.event_type == "CONCEDE"), None)
    concede_candidate = _build_concede_turning_point(concede_event) if concede_event is not None else None
    if concede_candidate is not None:
        scored_candidates.append(concede_candidate)

    if len(scored_candidates) < TURNING_POINTS_MAX_ITEMS:
        for event in events:
            if event.event_type not in {"KO", "PRIZE_TAKEN", "ATTACK"}:
                continue
            scored_candidates.append(_build_event_turning_point(event))

    scored_candidates.sort(key=lambda item: (-item[0], item[1], item[2].title))

    turning_points: list[TurningPoint] = []
    for _, _, candidate in scored_candidates:
        if len(turning_points) >= TURNING_POINTS_MAX_ITEMS:
            break
        if any(existing.evidence.start_line == candidate.evidence.start_line for existing in turning_points):
            continue
        turning_points.append(candidate)

    if concede_candidate is not None and all(tp.title != concede_candidate[2].title for tp in turning_points):
        if len(turning_points) < TURNING_POINTS_MAX_ITEMS:
            turning_points.append(concede_candidate[2])
        else:
            turning_points[-1] = concede_candidate[2]

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
    match_facts = extract_match_facts(log_text)
    play_bundles = extract_play_bundles(log_text)
    summary = _summary_from_context(log_text, match_facts)
    fallback_summary = list(summary[:SUMMARY_MAX_ITEMS])

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
        fallback_summary=fallback_summary,
        fallback_next_actions=next_actions,
    )
    if llm_guidance is not None:
        summary = llm_guidance.summary
        next_actions = llm_guidance.next_actions
    summary, unknowns = apply_summary_claim_integrity(
        summary=summary[:SUMMARY_MAX_ITEMS],
        unknowns=unknowns,
        fallback_summary=fallback_summary,
        log_text=log_text,
    )

    return PostGameReport(
        summary=summary[:SUMMARY_MAX_ITEMS],
        turning_points=turning_points,
        mistakes=mistakes,
        unknowns=unknowns,
        next_actions=next_actions,
        match_facts=match_facts,
        play_bundles=play_bundles,
    )
