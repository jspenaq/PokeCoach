from __future__ import annotations

from pokecoach.coach_auditor import evaluate_quality_minimum, run_one_iteration_coach_auditor
from pokecoach.schemas import AuditResult, DraftReport, PatchAction, Violation


def _make_draft(tag: str) -> DraftReport:
    return DraftReport(
        summary=[f"{tag} summary"],
        next_actions=[f"{tag} action"],
        turning_points_picks=[f"{tag}-tp-1"],
        mistakes_picks=[f"{tag}-ms-1"],
        unknowns=[],
    )


def _make_violation(
    *,
    code: str = "EVIDENCE_MISSING",
    severity: str = "critical",
    field: str = "summary[0]",
) -> Violation:
    return Violation(
        code=code,
        severity=severity,
        field=field,
        message="Claim without evidence.",
        suggested_fix="Replace with deterministic candidate.",
    )


def test_run_one_iteration_passes_on_first_audit_without_rewrite() -> None:
    calls = {"draft": 0, "audit": 0, "rewrite": 0}

    def draft_generator() -> DraftReport:
        calls["draft"] += 1
        return _make_draft("initial")

    def auditor(_draft: DraftReport) -> AuditResult:
        calls["audit"] += 1
        return AuditResult(
            quality_minimum_pass=True,
            violations=[],
            patch_plan=[],
            audit_summary="Pass.",
        )

    def rewrite_generator(
        _draft: DraftReport, _violations: list[Violation], _patch_plan: list[PatchAction]
    ) -> DraftReport:
        calls["rewrite"] += 1
        return _make_draft("rewritten")

    result = run_one_iteration_coach_auditor(draft_generator, auditor, rewrite_generator)

    assert result.draft_report.summary == ["initial summary"]
    assert result.metadata.audit_status == "pass"
    assert result.metadata.violations_count == 0
    assert result.metadata.rewrite_used is False
    assert calls == {"draft": 1, "audit": 1, "rewrite": 0}


def test_run_one_iteration_rewrites_once_after_failed_first_audit() -> None:
    calls = {"draft": 0, "audit": 0, "rewrite": 0}
    first_violation = _make_violation()
    patch_plan = [
        PatchAction(
            target="summary[0]",
            action="replace",
            replacement_source="turning_point_candidates[0]",
            reason="EVIDENCE_MISSING",
        )
    ]

    def draft_generator() -> DraftReport:
        calls["draft"] += 1
        return _make_draft("initial")

    def auditor(_draft: DraftReport) -> AuditResult:
        calls["audit"] += 1
        if calls["audit"] == 1:
            return AuditResult(
                quality_minimum_pass=False,
                violations=[first_violation],
                patch_plan=patch_plan,
                audit_summary="Fail first pass.",
            )
        return AuditResult(
            quality_minimum_pass=True,
            violations=[],
            patch_plan=[],
            audit_summary="Pass after rewrite.",
        )

    def rewrite_generator(
        draft: DraftReport, violations: list[Violation], incoming_patch_plan: list[PatchAction]
    ) -> DraftReport:
        calls["rewrite"] += 1
        assert draft.summary == ["initial summary"]
        assert violations == [first_violation]
        assert incoming_patch_plan == patch_plan
        return _make_draft("rewritten")

    result = run_one_iteration_coach_auditor(draft_generator, auditor, rewrite_generator)

    assert result.draft_report.summary == ["rewritten summary"]
    assert result.metadata.audit_status == "pass"
    assert result.metadata.violations_count == 0
    assert result.metadata.rewrite_used is True
    assert calls == {"draft": 1, "audit": 2, "rewrite": 1}


def test_run_one_iteration_returns_rewritten_output_when_second_audit_fails() -> None:
    calls = {"draft": 0, "audit": 0, "rewrite": 0}

    def draft_generator() -> DraftReport:
        calls["draft"] += 1
        return _make_draft("initial")

    def auditor(_draft: DraftReport) -> AuditResult:
        calls["audit"] += 1
        return AuditResult(
            quality_minimum_pass=False,
            violations=[_make_violation()],
            patch_plan=[],
            audit_summary="Still failing.",
        )

    def rewrite_generator(
        _draft: DraftReport, _violations: list[Violation], _patch_plan: list[PatchAction]
    ) -> DraftReport:
        calls["rewrite"] += 1
        return _make_draft("rewritten")

    result = run_one_iteration_coach_auditor(draft_generator, auditor, rewrite_generator)

    assert result.draft_report.summary == ["rewritten summary"]
    assert result.metadata.audit_status == "fail"
    assert result.metadata.violations_count == 1
    assert result.metadata.rewrite_used is True
    assert calls == {"draft": 1, "audit": 2, "rewrite": 1}


def test_evaluate_quality_minimum_fails_with_one_critical() -> None:
    assert evaluate_quality_minimum([_make_violation(severity="critical")]) is False


def test_evaluate_quality_minimum_fails_with_two_majors() -> None:
    violations = [
        _make_violation(code="FORMAT_CARDINALITY_SUMMARY", severity="major", field="summary"),
        _make_violation(code="FORMAT_CARDINALITY_ACTIONS", severity="major", field="next_actions"),
    ]
    assert evaluate_quality_minimum(violations) is False


def test_evaluate_quality_minimum_passes_with_one_major_only() -> None:
    violations = [_make_violation(code="CANDIDATE_DRIFT", severity="major", field="turning_points_picks")]
    assert evaluate_quality_minimum(violations) is True


def test_evaluate_quality_minimum_passes_with_only_minors() -> None:
    violations = [
        _make_violation(code="STYLE_VERBOSE", severity="minor"),
        _make_violation(code="STYLE_REDUNDANT", severity="minor"),
    ]
    assert evaluate_quality_minimum(violations) is True


def test_orchestration_normalizes_inconsistent_auditor_boolean_with_policy() -> None:
    calls = {"draft": 0, "audit": 0, "rewrite": 0}

    def draft_generator() -> DraftReport:
        calls["draft"] += 1
        return _make_draft("initial")

    def auditor(_draft: DraftReport) -> AuditResult:
        calls["audit"] += 1
        if calls["audit"] == 1:
            return AuditResult(
                quality_minimum_pass=True,
                violations=[_make_violation(severity="critical")],
                patch_plan=[],
                audit_summary="Inconsistent: critical but pass=true.",
            )
        return AuditResult(
            quality_minimum_pass=True,
            violations=[
                _make_violation(code="FORMAT_CARDINALITY_SUMMARY", severity="major", field="summary"),
                _make_violation(code="FORMAT_CARDINALITY_ACTIONS", severity="major", field="next_actions"),
            ],
            patch_plan=[],
            audit_summary="Inconsistent: two majors but pass=true.",
        )

    def rewrite_generator(
        _draft: DraftReport, _violations: list[Violation], _patch_plan: list[PatchAction]
    ) -> DraftReport:
        calls["rewrite"] += 1
        return _make_draft("rewritten")

    result = run_one_iteration_coach_auditor(draft_generator, auditor, rewrite_generator)

    assert result.draft_report.summary == ["rewritten summary"]
    assert result.metadata.audit_status == "fail"
    assert result.metadata.violations_count == 2
    assert result.metadata.rewrite_used is True
    assert calls == {"draft": 1, "audit": 2, "rewrite": 1}


def test_event_sequence_when_passes_on_first_audit() -> None:
    events: list[dict[str, object]] = []

    def draft_generator() -> DraftReport:
        return _make_draft("initial")

    def auditor(_draft: DraftReport) -> AuditResult:
        return AuditResult(
            quality_minimum_pass=True,
            violations=[],
            patch_plan=[],
            audit_summary="Pass.",
        )

    def rewrite_generator(
        _draft: DraftReport, _violations: list[Violation], _patch_plan: list[PatchAction]
    ) -> DraftReport:
        raise AssertionError("rewrite should not be called")

    result = run_one_iteration_coach_auditor(
        draft_generator,
        auditor,
        rewrite_generator,
        event_callback=events.append,
    )

    assert [event["event_name"] for event in events] == [
        "coach_run_started",
        "coach_run_completed",
        "audit_run_completed",
        "report_returned",
    ]
    assert result.metadata.events_count == 4
    assert result.metadata.audit_pass_first_try is True


def test_event_sequence_when_rewrite_is_used() -> None:
    events: list[dict[str, object]] = []
    calls = {"audit": 0}

    def draft_generator() -> DraftReport:
        return _make_draft("initial")

    def auditor(_draft: DraftReport) -> AuditResult:
        calls["audit"] += 1
        if calls["audit"] == 1:
            return AuditResult(
                quality_minimum_pass=False,
                violations=[_make_violation(severity="critical")],
                patch_plan=[],
                audit_summary="Fail first pass.",
            )
        return AuditResult(
            quality_minimum_pass=True,
            violations=[],
            patch_plan=[],
            audit_summary="Pass after rewrite.",
        )

    def rewrite_generator(
        _draft: DraftReport, _violations: list[Violation], _patch_plan: list[PatchAction]
    ) -> DraftReport:
        return _make_draft("rewritten")

    result = run_one_iteration_coach_auditor(
        draft_generator,
        auditor,
        rewrite_generator,
        event_callback=events.append,
    )

    assert [event["event_name"] for event in events] == [
        "coach_run_started",
        "coach_run_completed",
        "audit_run_completed",
        "audit_failed_quality_minimum",
        "rewrite_started",
        "rewrite_completed",
        "audit_run_completed",
        "report_returned",
    ]
    assert result.metadata.events_count == 8
    assert result.metadata.audit_pass_first_try is False


def test_callback_payloads_keep_expected_order_and_minimum_fields() -> None:
    events: list[dict[str, object]] = []

    def draft_generator() -> DraftReport:
        return _make_draft("initial")

    def auditor(_draft: DraftReport) -> AuditResult:
        return AuditResult(
            quality_minimum_pass=False,
            violations=[_make_violation(severity="critical")],
            patch_plan=[],
            audit_summary="Fail.",
        )

    def rewrite_generator(
        _draft: DraftReport, _violations: list[Violation], _patch_plan: list[PatchAction]
    ) -> DraftReport:
        return _make_draft("rewritten")

    run_one_iteration_coach_auditor(
        draft_generator,
        auditor,
        rewrite_generator,
        event_callback=events.append,
    )

    assert events[0]["event_name"] == "coach_run_started"
    assert events[-1]["event_name"] == "report_returned"
    for payload in events:
        assert "event_name" in payload
        assert "stage" in payload
        assert "violations_count" in payload
        assert "quality_minimum_pass" in payload
        assert "rewrite_used" in payload
