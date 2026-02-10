"""Minimal PoC using pydantic + pydantic-ai structured output."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent


class PoCReport(BaseModel):
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)


def build_mock_report() -> PoCReport:
    """Deterministic fallback for local runs without model credentials."""
    return PoCReport(
        summary="Mock mode: early-game sequencing looked stable with one missed optimization.",
        confidence=0.82,
    )


def run_agent_report(prompt: str, model_name: str) -> PoCReport:
    agent = Agent(
        model_name,
        output_type=PoCReport,
        system_prompt=(
            "You are a concise coaching assistant. Return only grounded, short feedback."
        ),
    )
    result = agent.run_sync(prompt)
    return result.output


def main() -> None:
    prompt = (
        "Create a very short post-game coaching report from this note: "
        "'Player kept tempo but delayed prize mapping and lost initiative on turn 4.'"
    )

    model_name = os.getenv("POKECOACH_PYDANTICAI_MODEL")
    api_key = os.getenv("OPENAI_API_KEY")

    if model_name and api_key:
        try:
            report = run_agent_report(prompt=prompt, model_name=model_name)
            mode = "agent"
        except Exception as exc:  # pragma: no cover - demo fallback
            print(f"Agent call failed, falling back to mock mode: {exc}")
            report = build_mock_report()
            mode = "mock"
    else:
        report = build_mock_report()
        mode = "mock"

    print(f"mode={mode}")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
