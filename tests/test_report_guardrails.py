from __future__ import annotations

from pokecoach import report
from pokecoach.schemas import EvidenceSpan, KeyEvent, KeyEventIndex, Mistake, TurningPoint


def _ev(line: int, text: str) -> EvidenceSpan:
    return EvidenceSpan(start_line=line, end_line=line, raw_lines=[text])


def _tp(title: str, confidence: float, line: int = 1) -> TurningPoint:
    return TurningPoint(
        title=title,
        impact="Impact",
        confidence=confidence,
        depends_on_hidden_info=False,
        evidence=_ev(line, f"event-{line}"),
    )


def _mistake(description: str, confidence: float, line: int = 1) -> Mistake:
    return Mistake(
        description=description,
        why_it_matters="Why",
        better_line="Better",
        confidence=confidence,
        depends_on_hidden_info=False,
        evidence=_ev(line, f"event-{line}"),
    )


def test_guardrails_remove_items_without_evidence(monkeypatch) -> None:
    bad_evidence = EvidenceSpan.model_construct(start_line=1, end_line=1, raw_lines=[])
    bad_tp = TurningPoint.model_construct(
        title="No evidence tp",
        impact="Impact",
        confidence=0.9,
        depends_on_hidden_info=False,
        evidence=bad_evidence,
    )
    bad_mistake = Mistake.model_construct(
        description="No evidence mistake",
        why_it_matters="Why",
        better_line="Better",
        confidence=0.9,
        depends_on_hidden_info=False,
        evidence=bad_evidence,
    )

    monkeypatch.setattr(
        report,
        "_build_turning_points",
        lambda _log: [_tp("TP1", 0.8, 1), _tp("TP2", 0.8, 2), bad_tp],
    )
    monkeypatch.setattr(
        report,
        "_build_mistakes",
        lambda _log: [
            _mistake("M1", 0.7, 1),
            _mistake("M2", 0.7, 2),
            _mistake("M3", 0.7, 3),
            bad_mistake,
        ],
    )

    built = report.generate_post_game_report("Jugador infligió 20 puntos de daño usando X.")

    assert len(built.turning_points) == 2
    assert len(built.mistakes) == 3
    assert all(item.evidence.raw_lines for item in built.turning_points)
    assert all(item.evidence.raw_lines for item in built.mistakes)


def test_guardrails_reroute_low_confidence_claims_to_unknowns(monkeypatch) -> None:
    monkeypatch.setattr(
        report,
        "_build_turning_points",
        lambda _log: [
            _tp("Solid TP1", 0.8, 1),
            _tp("Solid TP2", 0.8, 2),
            _tp("Duplicate low TP", 0.4, 3),
            _tp("Duplicate low TP", 0.2, 4),
        ],
    )
    monkeypatch.setattr(
        report,
        "_build_mistakes",
        lambda _log: [
            _mistake("Solid M1", 0.8, 1),
            _mistake("Solid M2", 0.8, 2),
            _mistake("Solid M3", 0.8, 3),
            _mistake("Duplicate low M", 0.4, 4),
            _mistake("Duplicate low M", 0.2, 5),
        ],
    )

    built = report.generate_post_game_report("Jugador infligió 20 puntos de daño usando X.")

    assert all(tp.confidence >= 0.55 for tp in built.turning_points)
    assert all(ms.confidence >= 0.55 for ms in built.mistakes)
    assert "Low-confidence turning point omitted: Duplicate low TP" in built.unknowns
    assert "Low-confidence mistake omitted: Duplicate low M" in built.unknowns
    assert built.unknowns.count("Low-confidence turning point omitted: Duplicate low TP") == 1
    assert built.unknowns.count("Low-confidence mistake omitted: Duplicate low M") == 1


def test_guardrails_backfill_minimum_cardinality_from_events(monkeypatch) -> None:
    monkeypatch.setattr(report, "_build_turning_points", lambda _log: [_tp("Low TP", 0.4, 1)])
    monkeypatch.setattr(report, "_build_mistakes", lambda _log: [_mistake("Low M", 0.4, 1)])
    monkeypatch.setattr(
        report,
        "find_key_events",
        lambda _log: KeyEventIndex(
            events=[KeyEvent(event_type="ATTACK", line=10, text="Jugador infligió 20 usando X.")]
        ),
    )

    built = report.generate_post_game_report("irrelevant")

    assert len(built.turning_points) == 2
    assert len(built.mistakes) == 3
    assert all(item.evidence.raw_lines for item in built.turning_points)
    assert all(item.evidence.raw_lines for item in built.mistakes)
    assert all(tp.confidence >= 0.55 for tp in built.turning_points)
    assert all(ms.confidence >= 0.55 for ms in built.mistakes)
