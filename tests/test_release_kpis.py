from pokecoach.quality_kpis import evaluate_release_kpis


def test_release_kpis_meet_phase5_thresholds() -> None:
    result = evaluate_release_kpis()

    assert result.actionable_claims > 0
    assert result.hallucination_rate == 0.0
    assert result.evidence_coverage == 1.0
    assert result.golden_stability == 1.0
