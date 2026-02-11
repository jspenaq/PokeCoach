"""One-iteration orchestration for Agentic Coach + Auditor."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

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


class CoachAuditorMetadata(BaseModel):
    audit_status: Literal["pass", "fail"]
    violations_count: int = Field(ge=0)
    rewrite_used: bool


class CoachAuditorRunResult(BaseModel):
    draft_report: DraftReport
    metadata: CoachAuditorMetadata


def run_one_iteration_coach_auditor(
    draft_generator: Callable[[], DraftReport],
    auditor: Callable[[DraftReport], AuditResult],
    rewrite_generator: Callable[[DraftReport, list[Violation], list[PatchAction]], DraftReport],
) -> CoachAuditorRunResult:
    """Run Agent A draft, Agent B audit, and at most one rewrite pass."""
    initial_draft = draft_generator()
    first_audit = auditor(initial_draft)
    first_pass = evaluate_quality_minimum(first_audit.violations)
    if first_pass:
        return CoachAuditorRunResult(
            draft_report=initial_draft,
            metadata=CoachAuditorMetadata(
                audit_status="pass",
                violations_count=len(first_audit.violations),
                rewrite_used=False,
            ),
        )

    rewritten_draft = rewrite_generator(initial_draft, first_audit.violations, first_audit.patch_plan)
    second_audit = auditor(rewritten_draft)
    second_pass = evaluate_quality_minimum(second_audit.violations)
    return CoachAuditorRunResult(
        draft_report=rewritten_draft,
        metadata=CoachAuditorMetadata(
            audit_status="pass" if second_pass else "fail",
            violations_count=len(second_audit.violations),
            rewrite_used=True,
        ),
    )
