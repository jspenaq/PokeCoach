from pokecoach.schemas import EvidenceSpan, MatchFacts, Mistake, PostGameReport, TurningPoint


def test_post_game_report_minimal_valid() -> None:
    evidence = EvidenceSpan(start_line=10, end_line=10, raw_lines=["KO event"])

    turning_points = [
        TurningPoint(
            title="TP1",
            impact="Momentum swing",
            confidence=0.8,
            depends_on_hidden_info=False,
            evidence=evidence,
        ),
        TurningPoint(
            title="TP2",
            impact="Second swing",
            confidence=0.7,
            depends_on_hidden_info=True,
            evidence=evidence,
        ),
    ]

    mistakes = [
        Mistake(
            description="M1",
            why_it_matters="Reason",
            better_line="Alternative",
            confidence=0.7,
            depends_on_hidden_info=False,
            evidence=evidence,
        ),
        Mistake(
            description="M2",
            why_it_matters="Reason",
            better_line="Alternative",
            confidence=0.6,
            depends_on_hidden_info=True,
            evidence=evidence,
        ),
        Mistake(
            description="M3",
            why_it_matters="Reason",
            better_line="Alternative",
            confidence=0.65,
            depends_on_hidden_info=False,
            evidence=evidence,
        ),
    ]

    report = PostGameReport(
        summary=["a", "b", "c", "d", "e"],
        turning_points=turning_points,
        mistakes=mistakes,
        unknowns=["Hidden prizes"],
        next_actions=["A1", "A2", "A3"],
    )

    assert len(report.summary) == 5
    assert report.match_facts == MatchFacts()


def test_post_game_report_allows_explicit_match_facts() -> None:
    evidence = EvidenceSpan(start_line=10, end_line=10, raw_lines=["KO event"])

    report = PostGameReport(
        summary=["a", "b", "c", "d", "e"],
        turning_points=[
            TurningPoint(
                title="TP1",
                impact="Momentum swing",
                confidence=0.8,
                depends_on_hidden_info=False,
                evidence=evidence,
            ),
            TurningPoint(
                title="TP2",
                impact="Second swing",
                confidence=0.7,
                depends_on_hidden_info=True,
                evidence=evidence,
            ),
        ],
        mistakes=[
            Mistake(
                description="M1",
                why_it_matters="Reason",
                better_line="Alternative",
                confidence=0.7,
                depends_on_hidden_info=False,
                evidence=evidence,
            ),
            Mistake(
                description="M2",
                why_it_matters="Reason",
                better_line="Alternative",
                confidence=0.6,
                depends_on_hidden_info=True,
                evidence=evidence,
            ),
            Mistake(
                description="M3",
                why_it_matters="Reason",
                better_line="Alternative",
                confidence=0.65,
                depends_on_hidden_info=False,
                evidence=evidence,
            ),
        ],
        next_actions=["A1", "A2", "A3"],
        match_facts=MatchFacts(
            winner="Alice",
            went_first_player="Bob",
            turns_count=9,
            observable_prizes_taken_by_player={"Alice": 3},
            kos_by_player={"Bob": 1},
            concede=True,
        ),
    )

    assert report.match_facts.winner == "Alice"
    assert report.match_facts.turns_count == 9
