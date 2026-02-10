"""Deterministic KPI checks for release quality gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pokecoach.report import generate_post_game_report
from pokecoach.tools import find_key_events, index_turns


@dataclass(frozen=True)
class ReleaseKPIResult:
    hallucination_rate: float
    evidence_coverage: float
    golden_stability: float
    actionable_claims: int


def _claims_with_evidence(log_path: Path) -> tuple[int, int]:
    report = generate_post_game_report(log_path.read_text(encoding="utf-8"))
    claims = [*report.turning_points, *report.mistakes]
    total = len(claims)
    with_evidence = sum(1 for claim in claims if any(line.strip() for line in claim.evidence.raw_lines))
    return total, with_evidence


def _golden_minimums_pass_rate(logs_dir: Path, expected_minimums_path: Path) -> float:
    expected = json.loads(expected_minimums_path.read_text(encoding="utf-8"))
    total = len(expected)
    passed = 0

    for log_name, minimums in expected.items():
        log_text = (logs_dir / log_name).read_text(encoding="utf-8")
        turns = index_turns(log_text)
        events = find_key_events(log_text).events

        attack_count = sum(1 for event in events if event.event_type == "ATTACK")
        ko_count = sum(1 for event in events if event.event_type == "KO")
        has_concede = any(event.event_type == "CONCEDE" for event in events)

        passes = (
            len(turns) >= int(minimums["min_turns"])
            and attack_count >= int(minimums["min_attacks"])
            and ko_count >= int(minimums["min_kos"])
            and has_concede is bool(minimums["has_concede"])
        )
        if passes:
            passed += 1

    return 1.0 if total == 0 else passed / total


def evaluate_release_kpis(
    logs_dir: Path = Path("logs_prueba"),
    expected_minimums_path: Path = Path("tests/golden/expected_minimums.json"),
) -> ReleaseKPIResult:
    log_paths = sorted(logs_dir.glob("battle_logs_ptcgl_spanish*.txt"))

    total_claims = 0
    evidence_claims = 0
    for log_path in log_paths:
        claims, with_evidence = _claims_with_evidence(log_path)
        total_claims += claims
        evidence_claims += with_evidence

    hallucinations = max(total_claims - evidence_claims, 0)
    hallucination_rate = 0.0 if total_claims == 0 else hallucinations / total_claims
    evidence_coverage = 1.0 if total_claims == 0 else evidence_claims / total_claims
    golden_stability = _golden_minimums_pass_rate(logs_dir, expected_minimums_path)

    return ReleaseKPIResult(
        hallucination_rate=hallucination_rate,
        evidence_coverage=evidence_coverage,
        golden_stability=golden_stability,
        actionable_claims=total_claims,
    )
