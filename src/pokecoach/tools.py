"""Deterministic tools for parser implementation."""

from __future__ import annotations

import re

from pokecoach.events.registry import EVENT_DETECTORS, SUPPORTER_KEYWORDS
from pokecoach.schemas import (
    KeyEvent,
    KeyEventIndex,
    MatchFacts,
    MatchStats,
    PlayBundle,
    PlayBundleEvent,
    TurnSpan,
    TurnSummary,
)

TURN_HEADER_RE = re.compile(r"^Turno de \[playerName\]\s*$")
ACTOR_PREFIX_RE = re.compile(r"^([A-Za-z0-9_\-]+)\s")
ACTOR_STOPLIST = {"El", "Se", "¡El", "-", "•", "Preparación", "Chequeo", "Resumen"}
PLAYER_ACTION_VERB_RE = re.compile(
    r"\b(?:robó|jugó|puso|unió|hizo|retiró|terminó|eligió|decidió|descartó|tomó|usó|infligió)\b",
    re.IGNORECASE,
)
PLAYER_INITIAL_DRAW_RE = re.compile(r"^([A-Za-z0-9_\-]+) robó 7 cartas de la mano inicial\.$")
PRIZE_TAKEN_RE = re.compile(r"^([A-Za-z0-9_\-]+) tomó (una|\d+) cartas? de Premio\.$")
CONCEDE_LINE_RE = re.compile(r"(?:El rival se rindió|Te rendiste)\.", re.IGNORECASE)
CONCEDE_WINNER_RE = re.compile(r"(?:El rival se rindió|Te rendiste)\.\s*([A-Za-z0-9_\-]+) ganó\.", re.IGNORECASE)
KO_OWNER_RE = re.compile(r"de ([A-Za-z0-9_\-]+) quedó Fuera de Combate", re.IGNORECASE)
KO_LOOKBACK_DEFAULT = 12
KO_LOOKBACK_MIN = 8
KO_LOOKBACK_MAX = 15
KO_CAUSAL_DAMAGE_RE = re.compile(r"\binfligió\s+\d+\s+puntos?\s+de\s+daño\b", re.IGNORECASE)
KO_CAUSAL_USED_RE = re.compile(r"\busó\b", re.IGNORECASE)
KO_CAUSAL_GUST_RE = re.compile(r"\bjugó\b.*\bÓrdenes de Jefes\b", re.IGNORECASE)
KO_CAUSAL_ACTOR_BEFORE_VERB_RE = re.compile(r"\bde ([A-Za-z0-9_\-]+)\s+(?:usó|infligió)\b", re.IGNORECASE)
PLAY_BUNDLE_GUST_RE = re.compile(r"\bjugó\b.*\bÓrdenes de Jefes\b", re.IGNORECASE)
PLAY_BUNDLE_ACTION_RE = re.compile(r"(?:\busó\b|\binfligió\b.*\busando\b)", re.IGNORECASE)
PLAY_BUNDLE_KO_RE = re.compile(r"quedó Fuera de Combate", re.IGNORECASE)


def _infer_actor(lines: list[str]) -> str | None:
    for line in lines:
        actor = infer_actor(line)
        if actor is not None:
            return actor
    return None


def infer_actor(line: str) -> str | None:
    text = line.strip()
    if not text:
        return None

    tokens = text.split(maxsplit=1)
    if not tokens:
        return None
    if tokens[0] in ACTOR_STOPLIST:
        return None

    match = ACTOR_PREFIX_RE.match(text)
    if not match:
        return None
    actor = match.group(1)
    if actor in ACTOR_STOPLIST:
        return None
    if not PLAYER_ACTION_VERB_RE.search(text):
        return None
    return actor


def _actor_prefix_from_text(text: str) -> str | None:
    match = ACTOR_PREFIX_RE.match(text)
    if not match:
        return None
    return match.group(1)


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

        for detector in EVENT_DETECTORS:
            events.extend(detector(text, i, raw))

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


def _build_play_bundle_event(line_number: int, text: str) -> PlayBundleEvent:
    return PlayBundleEvent(
        line=line_number,
        text=text,
        evidence={"start_line": line_number, "end_line": line_number, "raw_lines": [text]},
    )


def _start_play_bundle(
    turn_span: TurnSpan,
    actor: str | None,
    gust_event: PlayBundleEvent | None = None,
    action_event: PlayBundleEvent | None = None,
) -> PlayBundle:
    return PlayBundle(
        turn_number=turn_span.turn_number,
        actor=actor,
        window={
            "start_line": turn_span.start_line,
            "end_line": turn_span.end_line,
            "raw_lines": [f"Turno {turn_span.turn_number}"],
        },
        gust_event=gust_event,
        action_event=action_event,
    )


def _build_play_bundle_window_raw_lines(
    gust_event: PlayBundleEvent | None,
    action_event: PlayBundleEvent | None,
    ko_events: list[PlayBundleEvent],
    prize_events: list[PlayBundleEvent],
) -> list[str]:
    evidence_events: list[PlayBundleEvent] = []
    if gust_event is not None:
        evidence_events.append(gust_event)
    if action_event is not None:
        evidence_events.append(action_event)
    evidence_events.extend(ko_events)
    evidence_events.extend(prize_events)
    ordered_events = sorted(evidence_events, key=lambda event: event.line)
    return [event.text for event in ordered_events]


def _parse_prize_count(prize_text: str) -> int:
    match = PRIZE_TAKEN_RE.match(prize_text.strip())
    if not match:
        return 0
    count_text = match.group(2)
    return 1 if count_text == "una" else int(count_text)


def _pick_primary_action_index(
    action_events: list[PlayBundleEvent],
    action_ko_events: list[list[PlayBundleEvent]],
    action_prize_events: list[list[PlayBundleEvent]],
) -> int:
    ranked = []
    for index, action_event in enumerate(action_events):
        ko_count = len(action_ko_events[index])
        prize_total = sum(_parse_prize_count(event.text) for event in action_prize_events[index])
        prize_event_count = len(action_prize_events[index])
        ranked.append((ko_count, prize_total, prize_event_count, action_event.line, index))
    return max(ranked)[4]


def extract_play_bundles(log_text: str) -> list[PlayBundle]:
    lines = log_text.splitlines()
    turns = index_turns(log_text)
    bundles: list[PlayBundle] = []

    for turn_span in turns:
        window_lines = lines[turn_span.start_line - 1 : turn_span.end_line]
        actor = turn_span.actor or _infer_actor(window_lines[1:])
        gust_events: list[PlayBundleEvent] = []
        action_events: list[PlayBundleEvent] = []
        action_ko_events: list[list[PlayBundleEvent]] = []
        action_prize_events: list[list[PlayBundleEvent]] = []
        unscoped_ko_events: list[PlayBundleEvent] = []
        unscoped_prize_events: list[PlayBundleEvent] = []
        current_action_index: int | None = None

        for offset, raw in enumerate(window_lines):
            text = raw.strip()
            if not text:
                continue
            line_number = turn_span.start_line + offset

            if PLAY_BUNDLE_GUST_RE.search(text):
                gust_events.append(_build_play_bundle_event(line_number, raw))
                continue

            if PLAY_BUNDLE_ACTION_RE.search(text):
                action_events.append(_build_play_bundle_event(line_number, raw))
                action_ko_events.append([])
                action_prize_events.append([])
                current_action_index = len(action_events) - 1
                continue

            if PLAY_BUNDLE_KO_RE.search(text):
                event = _build_play_bundle_event(line_number, raw)
                if current_action_index is None:
                    unscoped_ko_events.append(event)
                else:
                    action_ko_events[current_action_index].append(event)

            prize_match = PRIZE_TAKEN_RE.match(text)
            if prize_match:
                event = _build_play_bundle_event(line_number, raw)
                if current_action_index is None:
                    unscoped_prize_events.append(event)
                else:
                    action_prize_events[current_action_index].append(event)

        primary_action: PlayBundleEvent | None = None
        ko_events: list[PlayBundleEvent] = list(unscoped_ko_events)
        prize_events: list[PlayBundleEvent] = list(unscoped_prize_events)
        if action_events:
            primary_action_index = _pick_primary_action_index(action_events, action_ko_events, action_prize_events)
            primary_action = action_events[primary_action_index]
            ko_events.extend(action_ko_events[primary_action_index])
            prize_events.extend(action_prize_events[primary_action_index])

        gust_event: PlayBundleEvent | None = None
        if gust_events:
            if primary_action is None:
                gust_event = gust_events[-1]
            else:
                gust_before_action = [event for event in gust_events if event.line < primary_action.line]
                if gust_before_action:
                    gust_event = gust_before_action[-1]

        bundle = _start_play_bundle(
            turn_span=turn_span,
            actor=actor,
            gust_event=gust_event,
            action_event=primary_action,
        )
        bundle.ko_events = ko_events
        bundle.prize_events = prize_events
        bundle.window.raw_lines = _build_play_bundle_window_raw_lines(
            gust_event=bundle.gust_event,
            action_event=bundle.action_event,
            ko_events=bundle.ko_events,
            prize_events=bundle.prize_events,
        )
        if bundle.gust_event or bundle.action_event or bundle.ko_events or bundle.prize_events:
            bundles.append(bundle)

    return bundles


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

        prize_match = PRIZE_TAKEN_RE.match(text)
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


def _collect_players(log_text: str) -> list[str]:
    players: list[str] = []
    for raw in log_text.splitlines():
        text = raw.strip()
        draw_match = PLAYER_INITIAL_DRAW_RE.match(text)
        if draw_match:
            player = draw_match.group(1)
            if player not in players:
                players.append(player)
            continue
        actor = infer_actor(text)
        if actor and actor not in players:
            players.append(actor)
    return players


def _resolve_ko_lookback_window(ko_lookback_window: int | None) -> int:
    if ko_lookback_window is None:
        return KO_LOOKBACK_DEFAULT
    return max(KO_LOOKBACK_MIN, min(KO_LOOKBACK_MAX, ko_lookback_window))


def _turn_floor_idx(lines: list[str], idx: int) -> int:
    for prev_idx in range(idx, -1, -1):
        if TURN_HEADER_RE.match(lines[prev_idx].strip()):
            return prev_idx
    return 0


def _extract_causal_actor(text: str, players: list[str]) -> str | None:
    inferred = infer_actor(text)
    if inferred and inferred in players:
        return inferred

    match = KO_CAUSAL_ACTOR_BEFORE_VERB_RE.search(text)
    if match and match.group(1) in players:
        return match.group(1)

    return None


def _is_causal_ko_event(text: str) -> bool:
    return bool(KO_CAUSAL_DAMAGE_RE.search(text) or KO_CAUSAL_USED_RE.search(text) or KO_CAUSAL_GUST_RE.search(text))


def _infer_ko_actor(
    lines: list[str],
    idx: int,
    players: list[str],
    ko_lookback_window: int,
) -> str | None:
    floor_by_window = max(0, idx - ko_lookback_window)
    floor_by_turn = _turn_floor_idx(lines, idx)
    search_floor = max(floor_by_window, floor_by_turn)

    for prev_idx in range(idx - 1, search_floor - 1, -1):
        prev_text = lines[prev_idx].strip()
        if not prev_text:
            continue
        if not _is_causal_ko_event(prev_text):
            continue
        actor = _extract_causal_actor(prev_text, players)
        if actor:
            return actor
    return None


def extract_match_facts(log_text: str, ko_lookback_window: int | None = None) -> MatchFacts:
    lines = log_text.splitlines()
    players = _collect_players(log_text)
    stats = compute_basic_stats(log_text)
    resolved_ko_lookback_window = _resolve_ko_lookback_window(ko_lookback_window)

    concede = False
    winner: str | None = None
    kos_by_player: dict[str, int] = {}
    unknown_kos = 0

    for idx, raw in enumerate(lines):
        text = raw.strip()
        if not text:
            continue

        if CONCEDE_LINE_RE.search(text):
            concede = True
            winner_match = CONCEDE_WINNER_RE.search(text)
            if winner_match:
                winner = winner_match.group(1)

        ko_mentions = list(KO_OWNER_RE.finditer(text))
        if not ko_mentions:
            continue

        for mention in ko_mentions:
            owner = mention.group(1)
            ko_actor = _infer_ko_actor(lines, idx, players, resolved_ko_lookback_window)
            if ko_actor is None:
                unknown_kos += 1
                continue
            if ko_actor == owner:
                continue
            kos_by_player[ko_actor] = kos_by_player.get(ko_actor, 0) + 1

    if unknown_kos > 0:
        kos_by_player["unknown"] = unknown_kos

    return MatchFacts(
        winner=winner,
        went_first_player=stats.went_first_player,
        turns_count=len(index_turns(log_text)),
        observable_prizes_taken_by_player=dict(stats.observable_prizes_taken_by_player),
        kos_by_player=kos_by_player,
        concede=concede,
    )
