from __future__ import annotations

from pokecoach.coach_auditor import run_one_iteration_coach_auditor
from pokecoach.schemas import AuditResult, DraftReport, PatchAction, Violation


def _make_draft(tag: str) -> DraftReport:
    return DraftReport(
        summary=[f"{tag} summary"],
        next_actions=[f"{tag} action"],
        turning_points_picks=[f"{tag}-tp-1"],
        mistakes_picks=[f"{tag}-ms-1"],
        unknowns=[],
    )


def _make_violation() -> Violation:
    return Violation(
        code="EVIDENCE_MISSING",
        severity="critical",
        field="summary[0]",
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
