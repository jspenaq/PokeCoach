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
SPANISH_LOG_MARKERS_RE = re.compile(
    r"\b(turno de|fuera de combate|cartas? de premio|us[oó]|baraj[oó]|jug[oó])\b",
    re.IGNORECASE,
)
ENGLISH_OUTPUT_MARKERS_RE = re.compile(
    r"\b("
    r"observed|knockout|attack|turns? in the log|impact score|bonus|review|practice|rehearse|"
    r"momentum|unknown hidden information|concession ended"
    r")\b",
    re.IGNORECASE,
)
SPANISH_FALLBACK_SUMMARY_ITEMS = (
    "Los primeros turnos establecieron el estado inicial de la mesa.",
    "Los intercambios de mitad de partida influyeron en el ritmo.",
    "Las líneas de cierre dependieron de los recursos disponibles.",
)
SPANISH_DEFAULT_NEXT_ACTIONS = (
    "Practica el mapeo de Premios antes de cada ataque de alto impacto.",
    "Revisa la secuenciación de Partidarios en turnos con cambios de ritmo.",
    "Ensaya una lista de verificación antes de decidir ataque o retirada.",
)
SPANISH_MISTAKE_EVENT_WHY = "Esta secuencia afectó la presión de mesa y la carrera de Premios."
SPANISH_MISTAKE_EVENT_BETTER_LINE = "Reevalúa la secuencia antes de comprometer acciones clave."
SPANISH_MISTAKE_FALLBACK_DESCRIPTION = "Revisa la secuenciación del setup inicial."
SPANISH_MISTAKE_FALLBACK_WHY = "La secuenciación inicial condiciona las ventanas de ritmo posteriores."
SPANISH_MISTAKE_FALLBACK_BETTER_LINE = "Aplica una lista de verificación antes de atacar."
SPANISH_TURNING_POINT_FALLBACK_IMPACT = "La secuencia temprana probablemente moldeó el flujo de la partida."
SPANISH_TURNING_POINT_GENERIC_IMPACT = "Impacto observado en el ritmo o la presión de Premios."


def _is_spanish_log(log_text: str) -> bool:
    hits = sum(1 for line in log_text.splitlines() if SPANISH_LOG_MARKERS_RE.search(line))
    return hits >= 2


def _is_spanish_consistent_text(text: str) -> bool:
    return ENGLISH_OUTPUT_MARKERS_RE.search(text) is None


def _normalize_spanish_list(items: list[str], fallback: list[str], min_items: int, max_items: int) -> list[str]:
    normalized = [item for item in items if _is_spanish_consistent_text(item)]
    normalized = list(dict.fromkeys(normalized))
    for item in fallback:
        if len(normalized) >= min_items:
            break
        if item not in normalized:
            normalized.append(item)
    return normalized[:max_items]


def _event_type_label(event_type: str, spanish_mode: bool) -> str:
    if not spanish_mode:
        return event_type.lower()
    mapping = {"ATTACK": "ataque", "KO": "fuera de combate", "SUPPORTER": "partidario"}
    return mapping.get(event_type, event_type.lower())


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


def _build_bundle_turning_point(bundle, spanish_mode: bool) -> tuple[int, int, TurningPoint] | None:
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
    if spanish_mode:
        impact_parts = [f"Puntaje de impacto {score}: base por KO (+{IMPACT_KO_BASE})."]
    else:
        impact_parts = [f"Impact score {score}: KO base (+{IMPACT_KO_BASE})."]
    if has_two_prize_swing:
        if spanish_mode:
            impact_parts.append(f"Bono por swing de 2 Premios (+{IMPACT_TWO_PRIZE_SWING_BONUS}).")
        else:
            impact_parts.append(f"2-prize swing bonus (+{IMPACT_TWO_PRIZE_SWING_BONUS}).")
    if has_high_impact_target:
        if spanish_mode:
            impact_parts.append(f"Bono por objetivo de alto impacto (+{IMPACT_HIGH_IMPACT_TARGET_BONUS}).")
        else:
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


def _build_concede_turning_point(event: KeyEvent, spanish_mode: bool) -> tuple[int, int, TurningPoint]:
    impact = (
        f"Puntaje de impacto {IMPACT_CONCEDE_ENDGAME_SCORE}: la concesión cerró el estado final."
        if spanish_mode
        else f"Impact score {IMPACT_CONCEDE_ENDGAME_SCORE}: concession ended the game state."
    )
    return (
        IMPACT_CONCEDE_ENDGAME_SCORE,
        event.line,
        TurningPoint(
            title="Concede closes endgame",
            impact=impact,
            confidence=TURNING_POINT_EVENT_CONFIDENCE,
            depends_on_hidden_info=False,
            evidence=build_evidence_span(event.line, event.text),
        ),
    )


def _build_event_turning_point(event: KeyEvent, spanish_mode: bool) -> tuple[int, int, TurningPoint]:
    score = 10
    if event.event_type == "KO":
        score = IMPACT_KO_BASE
    elif event.event_type == "PRIZE_TAKEN":
        prizes = _extract_prize_count(event.text)
        score = 30 + (IMPACT_TWO_PRIZE_SWING_BONUS if prizes >= 2 else 0)
    elif event.event_type == "ATTACK":
        score = 10

    confidence = TURNING_POINT_EVENT_CONFIDENCE if event.event_type != "ATTACK" else TURNING_POINT_ATTACK_CONFIDENCE
    impact = (
        f"Puntaje de impacto {score}: ponderación determinista del impacto del evento."
        if spanish_mode
        else f"Impact score {score}: deterministic event impact weight."
    )
    return (
        score,
        event.line,
        TurningPoint(
            title=f"{event.event_type} swing",
            impact=impact,
            confidence=confidence,
            depends_on_hidden_info=event.event_type == "ATTACK",
            evidence=build_evidence_span(event.line, event.text),
        ),
    )


def _summary_from_context(log_text: str, match_facts: MatchFacts, spanish_mode: bool) -> list[str]:
    events = find_key_events(log_text).events

    summary: list[str] = []
    if match_facts.went_first_player:
        if spanish_mode:
            summary.append(f"{match_facts.went_first_player} tomó el primer turno.")
        else:
            summary.append(f"{match_facts.went_first_player} took the first turn.")

    ko_count = sum(match_facts.kos_by_player.values())
    prize_count = sum(match_facts.observable_prizes_taken_by_player.values())
    attack_count = sum(1 for event in events if event.event_type == "ATTACK")

    if spanish_mode:
        summary.append(f"Se observaron {attack_count} ataques en el registro.")
        summary.append(f"Se observaron {ko_count} Fuera de Combate.")
        summary.append(f"Se observaron {prize_count} cartas de Premio visibles tomadas.")
        summary.append(f"Se observaron {match_facts.turns_count} turnos en el registro.")
        summary.append("Los cambios de ritmo estuvieron impulsados por secuencias de ataque y KO.")
        summary.append("La información oculta puede cambiar la línea óptima.")
    else:
        summary.append(f"Observed {attack_count} attack events in the log.")
        summary.append(f"Observed {ko_count} knockout events.")
        summary.append(f"Observed {prize_count} observable prize cards taken.")
        summary.append(f"Observed {match_facts.turns_count} turns in the log.")
        summary.append("Momentum swings were driven by attack-to-KO sequences.")
        summary.append("Unknown hidden information may change optimal lines.")

    return summary[:SUMMARY_MAX_ITEMS]


def _build_turning_points(log_text: str, spanish_mode: bool) -> list[TurningPoint]:
    events = find_key_events(log_text).events
    scored_candidates: list[tuple[int, int, TurningPoint]] = []

    for bundle in extract_play_bundles(log_text):
        candidate = _build_bundle_turning_point(bundle, spanish_mode)
        if candidate is not None:
            scored_candidates.append(candidate)

    concede_event = next((event for event in events if event.event_type == "CONCEDE"), None)
    concede_candidate = _build_concede_turning_point(concede_event, spanish_mode) if concede_event is not None else None
    if concede_candidate is not None:
        scored_candidates.append(concede_candidate)

    if len(scored_candidates) < TURNING_POINTS_MAX_ITEMS:
        for event in events:
            if event.event_type not in {"KO", "PRIZE_TAKEN", "ATTACK"}:
                continue
            scored_candidates.append(_build_event_turning_point(event, spanish_mode))

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
                impact=SPANISH_TURNING_POINT_FALLBACK_IMPACT if spanish_mode else TURNING_POINT_FALLBACK_IMPACT,
                confidence=TURNING_POINT_FALLBACK_CONFIDENCE,
                depends_on_hidden_info=True,
                evidence=build_evidence_span(fallback.line, fallback.text),
            )
        )

    return turning_points[:TURNING_POINTS_MAX_ITEMS]


def _build_mistakes(log_text: str, spanish_mode: bool) -> list[Mistake]:
    events = find_key_events(log_text).events
    candidates = [event for event in events if event.event_type in {"ATTACK", "KO", "SUPPORTER"}]

    mistakes: list[Mistake] = []
    for event in candidates[:MISTAKES_MAX_ITEMS]:
        event_label = _event_type_label(event.event_type, spanish_mode)
        mistakes.append(
            Mistake(
                description=(
                    f"Revisa la decisión alrededor de un evento de {event_label}."
                    if spanish_mode
                    else MISTAKE_EVENT_DESCRIPTION.format(event_type=event_label)
                ),
                why_it_matters=SPANISH_MISTAKE_EVENT_WHY if spanish_mode else MISTAKE_EVENT_WHY,
                better_line=SPANISH_MISTAKE_EVENT_BETTER_LINE if spanish_mode else MISTAKE_EVENT_BETTER_LINE,
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
                description=SPANISH_MISTAKE_FALLBACK_DESCRIPTION if spanish_mode else MISTAKE_FALLBACK_DESCRIPTION,
                why_it_matters=SPANISH_MISTAKE_FALLBACK_WHY if spanish_mode else MISTAKE_FALLBACK_WHY,
                better_line=SPANISH_MISTAKE_FALLBACK_BETTER_LINE if spanish_mode else MISTAKE_FALLBACK_BETTER_LINE,
                confidence=MISTAKE_FALLBACK_CONFIDENCE,
                depends_on_hidden_info=True,
                evidence=build_evidence_span(fallback.line, fallback.text),
            )
        )

    return mistakes[:MISTAKES_MAX_ITEMS]


def generate_post_game_report(log_text: str) -> PostGameReport:
    spanish_mode = _is_spanish_log(log_text)
    turns = index_turns(log_text)
    match_facts = extract_match_facts(log_text)
    play_bundles = extract_play_bundles(log_text)
    summary = _summary_from_context(log_text, match_facts, spanish_mode)
    fallback_summary = list(summary[:SUMMARY_MAX_ITEMS])

    if len(summary) < 5:
        summary.extend(SPANISH_FALLBACK_SUMMARY_ITEMS if spanish_mode else FALLBACK_SUMMARY_ITEMS)

    unknowns = list(DEFAULT_UNKNOWNS)
    if turns and turns[0].actor is None:
        unknowns.append(UNKNOWN_INFERRED_TURN_ACTORS)

    next_actions = list(SPANISH_DEFAULT_NEXT_ACTIONS if spanish_mode else DEFAULT_NEXT_ACTIONS)

    turning_points, mistakes, unknowns = apply_report_guardrails(
        log_text=log_text,
        turning_points=_build_turning_points(log_text, spanish_mode),
        mistakes=_build_mistakes(log_text, spanish_mode),
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
        spanish_mode=spanish_mode,
    )
    if spanish_mode:
        summary = _normalize_spanish_list(summary, fallback_summary, min_items=5, max_items=SUMMARY_MAX_ITEMS)
        next_actions = _normalize_spanish_list(
            next_actions,
            list(SPANISH_DEFAULT_NEXT_ACTIONS),
            min_items=3,
            max_items=len(SPANISH_DEFAULT_NEXT_ACTIONS),
        )
        turning_points = [
            tp
            if _is_spanish_consistent_text(tp.impact)
            else tp.model_copy(update={"impact": SPANISH_TURNING_POINT_GENERIC_IMPACT})
            for tp in turning_points
        ]
        normalized_mistakes: list[Mistake] = []
        for mistake in mistakes:
            normalized_mistakes.append(
                mistake.model_copy(
                    update={
                        "description": (
                            mistake.description
                            if _is_spanish_consistent_text(mistake.description)
                            else SPANISH_MISTAKE_FALLBACK_DESCRIPTION
                        ),
                        "why_it_matters": (
                            mistake.why_it_matters
                            if _is_spanish_consistent_text(mistake.why_it_matters)
                            else SPANISH_MISTAKE_FALLBACK_WHY
                        ),
                        "better_line": (
                            mistake.better_line
                            if _is_spanish_consistent_text(mistake.better_line)
                            else SPANISH_MISTAKE_FALLBACK_BETTER_LINE
                        ),
                    }
                )
            )
        mistakes = normalized_mistakes

    return PostGameReport(
        summary=summary[:SUMMARY_MAX_ITEMS],
        turning_points=turning_points,
        mistakes=mistakes,
        unknowns=unknowns,
        next_actions=next_actions,
        match_facts=match_facts,
        play_bundles=play_bundles,
    )
