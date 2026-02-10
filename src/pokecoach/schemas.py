"""Core typed contracts for PokeCoach reports (spec_v1)."""

from __future__ import annotations

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
    went_first: str | None = None
    mulligans_self: int | None = None
    mulligans_opponent: int | None = None
    observable_prizes_taken_self: int | None = None
    observable_prizes_taken_opponent: int | None = None


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


class PostGameReport(BaseModel):
    summary: list[str] = Field(min_length=5, max_length=8)
    turning_points: list[TurningPoint] = Field(min_length=2, max_length=4)
    mistakes: list[Mistake] = Field(min_length=3, max_length=6)
    unknowns: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(min_length=3, max_length=5)
