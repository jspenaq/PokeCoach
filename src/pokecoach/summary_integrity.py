"""Deterministic integrity validation for summary claims."""

from __future__ import annotations

import re

from pokecoach.constants import SUMMARY_MAX_ITEMS

TURN_HEADER_RE = re.compile(r"^Turno de \[playerName\]\s*$")
KO_LINE_RE = re.compile(r"quedó Fuera de Combate", re.IGNORECASE)
KO_CLAIM_RE = re.compile(
    r"^\s*(?P<actor>.+?)\s+\bKO\b\s+(?P<target>.+?)\s*[.!?]?\s*$",
    re.IGNORECASE,
)
CAUSAL_LINE_RE = re.compile(r"\b(?:usó|infligió|jugó)\b", re.IGNORECASE)
DEFAULT_WINDOW = 12


def apply_summary_claim_integrity(
    *,
    summary: list[str],
    unknowns: list[str],
    fallback_summary: list[str],
    log_text: str,
    spanish_mode: bool = False,
) -> tuple[list[str], list[str]]:
    """Validate summary bullets and rewrite/drop unverifiable KO attribution claims."""
    lines = log_text.splitlines()
    normalized_unknowns = list(dict.fromkeys(unknowns))
    unknown_seen = set(normalized_unknowns)
    normalized_summary: list[str] = []

    for bullet in summary:
        claim = _extract_ko_claim(bullet)
        if claim is None:
            normalized_summary.append(bullet)
            continue

        actor, target = claim
        verification = _verify_ko_claim(actor=actor, target=target, lines=lines)
        if verification == "verified":
            normalized_summary.append(bullet)
            continue
        if verification == "target_only":
            if spanish_mode:
                normalized_summary.append(f"Fuera de Combate observado: {target} quedó Fuera de Combate.")
            else:
                normalized_summary.append(f"Observed knockout: {target} was knocked out.")
            continue

        if spanish_mode:
            unknown = f"Afirmación de KO no verificable omitida del resumen: {bullet}"
        else:
            unknown = f"Unverifiable KO summary claim omitted: {bullet}"
        if unknown not in unknown_seen:
            normalized_unknowns.append(unknown)
            unknown_seen.add(unknown)

    normalized_summary = list(dict.fromkeys(normalized_summary))
    for fallback in fallback_summary:
        if len(normalized_summary) >= 5:
            break
        if fallback not in normalized_summary:
            normalized_summary.append(fallback)

    return normalized_summary[:SUMMARY_MAX_ITEMS], normalized_unknowns


def _extract_ko_claim(text: str) -> tuple[str, str] | None:
    match = KO_CLAIM_RE.fullmatch(text.strip())
    if not match:
        return None
    actor = match.group("actor").strip()
    target = match.group("target").strip()
    if not actor or not target:
        return None
    return actor, target


def _verify_ko_claim(*, actor: str, target: str, lines: list[str]) -> str:
    actor_norm = _normalize(actor)
    target_norm = _normalize(target)
    ko_lines: list[int] = []

    for idx, raw in enumerate(lines):
        text = raw.strip()
        if not text:
            continue
        if not KO_LINE_RE.search(text):
            continue
        if target_norm in _normalize(text):
            ko_lines.append(idx)

    if not ko_lines:
        return "missing_target_ko"

    for ko_idx in ko_lines:
        if _has_causal_actor(actor_norm=actor_norm, ko_idx=ko_idx, lines=lines):
            return "verified"
    return "target_only"


def _has_causal_actor(*, actor_norm: str, ko_idx: int, lines: list[str]) -> bool:
    lower_bound = max(0, ko_idx - DEFAULT_WINDOW)
    for idx in range(ko_idx - 1, lower_bound - 1, -1):
        text = lines[idx].strip()
        if not text:
            continue
        if TURN_HEADER_RE.match(text):
            break
        if not CAUSAL_LINE_RE.search(text):
            continue
        if actor_norm in _normalize(text):
            return True
    return False


def _normalize(value: str) -> str:
    lowered = value.lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(cleaned.split())
