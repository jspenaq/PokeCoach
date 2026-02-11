"""One-iteration orchestration for Agentic Coach + Auditor."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field

from pokecoach.schemas import AuditResult, DraftReport, PatchAction, Violation


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
    if first_audit.quality_minimum_pass:
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
    return CoachAuditorRunResult(
        draft_report=rewritten_draft,
        metadata=CoachAuditorMetadata(
            audit_status="pass" if second_audit.quality_minimum_pass else "fail",
            violations_count=len(second_audit.violations),
            rewrite_used=True,
        ),
    )
