"""One-iteration orchestration for Agentic Coach + Auditor."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field

from pokecoach.schemas import AuditResult, DraftReport, PatchAction, Violation


def evaluate_quality_minimum(violations: list[Violation]) -> bool:
    """Return pass/fail based on PRD-013 thresholds."""
    critical_count = sum(1 for violation in violations if violation.severity == "critical")
    major_count = sum(1 for violation in violations if violation.severity == "major")
    if critical_count >= 1:
        return False
    if major_count >= 2:
        return False
    return True


CoachAuditorEventName = Literal[
    "coach_run_started",
    "coach_run_completed",
    "audit_run_completed",
    "audit_failed_quality_minimum",
    "rewrite_started",
    "rewrite_completed",
    "report_returned",
]


class CoachAuditorEvent(BaseModel):
    event_name: CoachAuditorEventName
    stage: Literal["coach", "audit", "orchestrator"]
    violations_count: int = Field(default=0, ge=0)
    quality_minimum_pass: bool | None = None
    rewrite_used: bool | None = None


class CoachAuditorMetadata(BaseModel):
    audit_status: Literal["pass", "fail"]
    violations_count: int = Field(ge=0)
    rewrite_used: bool
    events_count: int = Field(ge=1)
    audit_pass_first_try: bool


class CoachAuditorRunResult(BaseModel):
    draft_report: DraftReport
    metadata: CoachAuditorMetadata


def run_one_iteration_coach_auditor(
    draft_generator: Callable[[], DraftReport],
    auditor: Callable[[DraftReport], AuditResult],
    rewrite_generator: Callable[[DraftReport, list[Violation], list[PatchAction]], DraftReport],
    *,
    event_callback: Callable[[dict[str, Any]], None] | None = None,
) -> CoachAuditorRunResult:
    """Run Agent A draft, Agent B audit, and at most one rewrite pass."""

    events: list[CoachAuditorEvent] = []

    def emit(event: CoachAuditorEvent) -> None:
        events.append(event)
        if event_callback is not None:
            event_callback(event.model_dump())

    emit(CoachAuditorEvent(event_name="coach_run_started", stage="coach"))
    initial_draft = draft_generator()
    emit(CoachAuditorEvent(event_name="coach_run_completed", stage="coach", rewrite_used=False))

    first_audit = auditor(initial_draft)
    first_pass = evaluate_quality_minimum(first_audit.violations)
    emit(
        CoachAuditorEvent(
            event_name="audit_run_completed",
            stage="audit",
            violations_count=len(first_audit.violations),
            quality_minimum_pass=first_pass,
            rewrite_used=False,
        )
    )

    if first_pass:
        emit(CoachAuditorEvent(event_name="report_returned", stage="orchestrator", rewrite_used=False))
        return CoachAuditorRunResult(
            draft_report=initial_draft,
            metadata=CoachAuditorMetadata(
                audit_status="pass",
                violations_count=len(first_audit.violations),
                rewrite_used=False,
                events_count=len(events),
                audit_pass_first_try=True,
            ),
        )

    emit(
        CoachAuditorEvent(
            event_name="audit_failed_quality_minimum",
            stage="orchestrator",
            violations_count=len(first_audit.violations),
            quality_minimum_pass=False,
            rewrite_used=False,
        )
    )
    emit(CoachAuditorEvent(event_name="rewrite_started", stage="coach", rewrite_used=True))
    rewritten_draft = rewrite_generator(initial_draft, first_audit.violations, first_audit.patch_plan)
    emit(CoachAuditorEvent(event_name="rewrite_completed", stage="coach", rewrite_used=True))

    second_audit = auditor(rewritten_draft)
    second_pass = evaluate_quality_minimum(second_audit.violations)
    emit(
        CoachAuditorEvent(
            event_name="audit_run_completed",
            stage="audit",
            violations_count=len(second_audit.violations),
            quality_minimum_pass=second_pass,
            rewrite_used=True,
        )
    )
    emit(
        CoachAuditorEvent(
            event_name="report_returned",
            stage="orchestrator",
            violations_count=len(second_audit.violations),
            quality_minimum_pass=second_pass,
            rewrite_used=True,
        )
    )
    return CoachAuditorRunResult(
        draft_report=rewritten_draft,
        metadata=CoachAuditorMetadata(
            audit_status="pass" if second_pass else "fail",
            violations_count=len(second_audit.violations),
            rewrite_used=True,
            events_count=len(events),
            audit_pass_first_try=False,
        ),
    )
