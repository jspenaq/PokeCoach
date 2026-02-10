"""Core typed contracts for PokeCoach reports (spec_v1)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceSpan(BaseModel):
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    raw_lines: list[str] = Field(min_length=1)


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
