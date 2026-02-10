"""PydanticAI runtime provider helpers for optional OpenRouter inference."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ
from typing import Mapping

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_PYDANTICAI_MODEL = "openai/gpt-4o-mini"


@dataclass(frozen=True)
class PydanticAIRuntimeConfig:
    """Environment-driven runtime configuration for live PydanticAI usage."""

    openrouter_api_key: str | None
    openrouter_base_url: str
    model: str

    @property
    def live_mode_enabled(self) -> bool:
        return bool(self.openrouter_api_key and self.model.strip())


class LLMReportGuidance(BaseModel):
    """Optional fields the LLM can improve without breaking report contracts."""

    summary: list[str] = Field(min_length=5, max_length=8)
    next_actions: list[str] = Field(min_length=3, max_length=5)


def load_runtime_config(env: Mapping[str, str] | None = None) -> PydanticAIRuntimeConfig:
    """Load OpenRouter/PydanticAI settings from environment variables."""
    if env is None:
        load_dotenv()
    values = environ if env is None else env
    return PydanticAIRuntimeConfig(
        openrouter_api_key=values.get("OPENROUTER_API_KEY"),
        openrouter_base_url=values.get("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
        model=values.get("POKECOACH_PYDANTICAI_MODEL", DEFAULT_PYDANTICAI_MODEL),
    )


def maybe_generate_guidance(
    *,
    log_text: str,
    fallback_summary: list[str],
    fallback_next_actions: list[str],
    config: PydanticAIRuntimeConfig | None = None,
) -> LLMReportGuidance | None:
    """Return LLM guidance when runtime config is valid; otherwise deterministic fallback."""
    cfg = config or load_runtime_config()
    if not cfg.live_mode_enabled:
        return None

    prompt = (
        "You are improving a Pokemon TCG post-game coaching report.\n"
        "Return concise, evidence-aligned coaching text.\n"
        "Rules:\n"
        "- Keep each bullet to one sentence.\n"
        "- Do not invent hidden information.\n"
        "- Keep content grounded in the log text.\n\n"
        f"Fallback summary bullets:\n{_format_bullets(fallback_summary)}\n\n"
        f"Fallback next actions:\n{_format_bullets(fallback_next_actions)}\n\n"
        f"Battle log:\n{log_text}"
    )

    try:
        model = OpenAIChatModel(
            cfg.model,
            provider=OpenAIProvider(base_url=cfg.openrouter_base_url, api_key=cfg.openrouter_api_key),
        )
        agent = Agent(model, output_type=LLMReportGuidance)
        result = agent.run_sync(prompt)
    except Exception:
        return None

    return result.output


def _format_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)
