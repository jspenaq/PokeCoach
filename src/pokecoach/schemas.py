"""Core typed contracts for PokeCoach reports (spec_v1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EvidenceSpan(BaseModel):
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    raw_lines: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_line_window(self) -> "EvidenceSpan":
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self


class TurnSpan(BaseModel):
    turn_number: int = Field(ge=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    actor: str | None = None

    @model_validator(mode="after")
    def validate_line_window(self) -> "TurnSpan":
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self


class KeyEvent(BaseModel):
    event_type: str
    line: int = Field(ge=1)
    text: str = Field(min_length=1)


class KeyEventIndex(BaseModel):
    events: list[KeyEvent] = Field(default_factory=list)


class MatchStats(BaseModel):
    went_first_player: str | None = None
    mulligans_by_player: dict[str, int] = Field(default_factory=dict)
    observable_prizes_taken_by_player: dict[str, int] = Field(default_factory=dict)


class TurnSummary(BaseModel):
    turn_number: int = Field(ge=1)
    bullets: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class TurningPoint(BaseModel):
    title: str = Field(min_length=1)
    impact: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    depends_on_hidden_info: bool
    evidence: EvidenceSpan


class Mistake(BaseModel):
    description: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    better_line: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    depends_on_hidden_info: bool
    evidence: EvidenceSpan


class MatchFacts(BaseModel):
    winner: str | None = None
    went_first_player: str | None = None
    turns_count: int = Field(default=0, ge=0)
    observable_prizes_taken_by_player: dict[str, int] = Field(default_factory=dict)
    kos_by_player: dict[str, int] = Field(default_factory=dict)
    concede: bool = False


class PlayBundleEvent(BaseModel):
    line: int = Field(ge=1)
    text: str = Field(min_length=1)
    evidence: EvidenceSpan


class PlayBundle(BaseModel):
    turn_number: int = Field(ge=1)
    actor: str | None = None
    window: EvidenceSpan
    gust_event: PlayBundleEvent | None = None
    action_event: PlayBundleEvent | None = None
    ko_events: list[PlayBundleEvent] = Field(default_factory=list)
    prize_events: list[PlayBundleEvent] = Field(default_factory=list)


class PostGameReport(BaseModel):
    summary: list[str] = Field(min_length=5, max_length=8)
    turning_points: list[TurningPoint] = Field(min_length=2, max_length=4)
    mistakes: list[Mistake] = Field(min_length=3, max_length=6)
    unknowns: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(min_length=3, max_length=5)
    match_facts: MatchFacts = Field(default_factory=MatchFacts)
    play_bundles: list[PlayBundle] = Field(default_factory=list)


class DraftReport(BaseModel):
    summary: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    turning_points_picks: list[str] = Field(default_factory=list)
    mistakes_picks: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class Violation(BaseModel):
    code: str = Field(min_length=1)
    severity: Literal["critical", "major", "minor"]
    field: str = Field(min_length=1)
    message: str = Field(min_length=1)
    suggested_fix: str = Field(min_length=1)


class PatchAction(BaseModel):
    target: str = Field(min_length=1)
    action: str = Field(min_length=1)
    replacement_source: str | None = None
    reason: str = Field(min_length=1)


class AuditResult(BaseModel):
    quality_minimum_pass: bool
    violations: list[Violation] = Field(default_factory=list)
    patch_plan: list[PatchAction] = Field(default_factory=list)
    audit_summary: str = Field(min_length=1)
