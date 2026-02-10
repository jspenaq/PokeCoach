"""Shared constants for report assembly and guardrails."""

from __future__ import annotations

MIN_CONFIDENCE = 0.55

SUMMARY_MAX_ITEMS = 8
TURNING_POINTS_MIN_ITEMS = 2
TURNING_POINTS_MAX_ITEMS = 4
MISTAKES_MIN_ITEMS = 3
MISTAKES_MAX_ITEMS = 6

UNKNOWN_LOW_CONF_TURNING_POINT = "Low-confidence turning point omitted: {title}"
UNKNOWN_LOW_CONF_MISTAKE = "Low-confidence mistake omitted: {description}"

FALLBACK_SUMMARY_ITEMS = (
    "Opening turns established initial board state.",
    "Mid-game exchanges influenced tempo.",
    "Endgame lines depended on available resources.",
)

DEFAULT_UNKNOWNS = (
    "Opponent hand information is incomplete.",
    "Prize card mapping is partially hidden unless revealed in the log.",
)
UNKNOWN_INFERRED_TURN_ACTORS = "Some turn actors were inferred due to placeholder turn headers."

DEFAULT_NEXT_ACTIONS = (
    "Practice prize mapping before each high-impact attack.",
    "Review supporter sequencing on turns with tempo swings.",
    "Rehearse a pre-commit checklist for attack and retreat decisions.",
)

TURNING_POINT_EVENT_IMPACT = "This event changed tempo or prize pressure."
TURNING_POINT_EVENT_CONFIDENCE = 0.75
TURNING_POINT_ATTACK_CONFIDENCE = 0.62
TURNING_POINT_FALLBACK_TITLE = "Early tempo signal"
TURNING_POINT_FALLBACK_IMPACT = "Early sequence likely shaped the game flow."
TURNING_POINT_FALLBACK_CONFIDENCE = 0.55

MISTAKE_EVENT_DESCRIPTION = "Review decision around {event_type} event."
MISTAKE_EVENT_WHY = "This sequence affected board pressure and prize race."
MISTAKE_EVENT_BETTER_LINE = "Re-evaluate sequencing before committing major actions."
MISTAKE_EVENT_CONFIDENCE = 0.64
MISTAKE_FALLBACK_DESCRIPTION = "Review early setup sequencing."
MISTAKE_FALLBACK_WHY = "Early sequencing influences later tempo windows."
MISTAKE_FALLBACK_BETTER_LINE = "Run pre-attack sequencing checklist."
MISTAKE_FALLBACK_CONFIDENCE = 0.55

PLACEHOLDER_TURNING_POINT_TITLE = "Evidence-backed tempo signal {seq}"
PLACEHOLDER_TURNING_POINT_IMPACT = "Observed event may have influenced tempo; verify board context."
PLACEHOLDER_TURNING_POINT_CONFIDENCE = 0.55
PLACEHOLDER_MISTAKE_DESCRIPTION = "Review sequencing around observed event."
PLACEHOLDER_MISTAKE_WHY = "Observed sequence may have narrowed available lines."
PLACEHOLDER_MISTAKE_BETTER_LINE = "Replay this turn and compare at least one alternative sequence."
PLACEHOLDER_MISTAKE_CONFIDENCE = 0.55
