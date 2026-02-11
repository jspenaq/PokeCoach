"""PydanticAI runtime provider helpers for optional OpenRouter inference."""

from __future__ import annotations

import re
import sys
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

_DEBUG_TRUTHY = {"1", "true", "yes", "on"}
_TOOL_CHOICE_AUTO_MODELS = {"z-ai/glm-4.5-air:free"}


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
    debug_enabled = _env_flag(environ, "POKECOACH_LLM_DEBUG")
    if not cfg.live_mode_enabled:
        if debug_enabled:
            _emit_debug("live mode disabled (missing OPENROUTER_API_KEY or model)")
        return None

    prompt = (
        "You are a deterministic Pokémon TCG battle-log reporter.\n"
        "You MUST stay grounded in the provided Battle log.\n\n"
        "OUTPUT:\n"
        "- Return JSON that matches the schema exactly.\n"
        "- summary: 5–8 bullets.\n"
        "- next_actions: 3–6 bullets max.\n"
        "- Each bullet: one short sentence.\n"
        "- Do NOT invent hidden information (hands, prizes, deck lists).\n\n"
        "# Pokemon TCG Rules Context\n"
        "WIN CONDITIONS: (1) Take all Prize cards, (2) Knock Out all opponent's Pokemon, "
        "(3) Opponent cannot draw at turn start.\n"
        "SETUP: 60-card deck, draw 7 cards, place 1 Basic Pokemon as Active, up to 5 on Bench, "
        "set aside 6 Prize cards face-down. When you Knock Out opponent's Pokemon, take 1 Prize card.\n"
        "TURN STRUCTURE: (1) Draw card, (2) Optional actions in any order: play Basic Pokemon to Bench, "
        "evolve Pokemon (not on first turn in play), attach 1 Energy per turn, play Trainer cards "
        "(1 Supporter max, 1 Stadium max), retreat Active Pokemon (pay Retreat Cost), use Abilities. "
        "(3) Attack with Active Pokemon (ends turn). First player skips attack on turn 1.\n"
        "ENERGY: Attacks require Energy cards attached. Match symbols in attack cost "
        "(any type works for colorless).\n"
        "EVOLUTION: Stage 1 evolves from Basic, Stage 2 from Stage 1. "
        "Keeps damage/attachments, clears Special Conditions.\n"
        "WEAKNESS/RESISTANCE: Some Pokemon take double damage (Weakness) "
        "or -20/-30 damage (Resistance) from certain types.\n"
        "RETREAT: Discard Energy equal to Retreat Cost to switch Active with Benched Pokemon (once per turn, "
        "cannot retreat if Asleep/Paralyzed).\n\n"
        "Coaching Guidelines:\n"
        "- Keep each bullet to one sentence.\n"
        "- Do not invent hidden information (hand, prizes, opponent's deck).\n"
        "- Keep content grounded in the log text.\n"
        "- Focus on observable mistakes: missed Energy attachments, poor retreat timing, suboptimal targeting, "
        "failing to evolve when possible, wasting Supporters.\n\n"
        f"Fallback summary bullets:\n{_format_bullets(fallback_summary)}\n\n"
        f"Fallback next actions:\n{_format_bullets(fallback_next_actions)}\n\n"
        f"Battle log:\n{log_text}"
    )

    model = OpenAIChatModel(
        cfg.model,
        provider=OpenAIProvider(base_url=cfg.openrouter_base_url, api_key=cfg.openrouter_api_key),
    )

    force_text_json = _model_requires_text_json_mode(cfg.model)
    if force_text_json and debug_enabled:
        _emit_debug(f"model={cfg.model} forced_mode=text_json")

    if force_text_json:
        return _run_text_json_guidance(
            model=model,
            prompt=prompt,
            debug_enabled=debug_enabled,
            model_name=cfg.model,
            base_url=cfg.openrouter_base_url,
        )

    structured_agent = Agent(model, output_type=LLMReportGuidance)
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            if debug_enabled:
                _emit_debug(f"attempt={attempt} mode=structured model={cfg.model} base_url={cfg.openrouter_base_url}")
            result = structured_agent.run_sync(prompt)
            if debug_enabled:
                _emit_debug(
                    f"live guidance ok attempt={attempt} summary_items={len(result.output.summary)} "
                    f"next_actions_items={len(result.output.next_actions)}"
                )
            return result.output
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if debug_enabled:
                _emit_debug(f"attempt={attempt} failed type={type(exc).__name__} detail={exc}")
            if _is_tool_choice_auto_error(exc):
                if debug_enabled:
                    _emit_debug("switching_mode=text_json reason=tool_choice_auto_requirement")
                return _run_text_json_guidance(
                    model=model,
                    prompt=prompt,
                    debug_enabled=debug_enabled,
                    model_name=cfg.model,
                    base_url=cfg.openrouter_base_url,
                )

    if debug_enabled and last_error is not None:
        _emit_debug(f"fallback=deterministic reason={type(last_error).__name__}")
    return None


def _run_text_json_guidance(
    *,
    model: OpenAIChatModel,
    prompt: str,
    debug_enabled: bool,
    model_name: str,
    base_url: str,
) -> LLMReportGuidance | None:
    text_agent = Agent(model, output_type=str)
    json_prompt = (
        f"{prompt}\n\n"
        "Return ONLY valid JSON with keys: summary, next_actions.\n"
        "Rules:\n"
        "- summary: array with 5 to 8 strings\n"
        "- next_actions: array with 3 to 5 strings\n"
        "- no markdown fences, no extra keys, no commentary"
    )

    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            if debug_enabled:
                _emit_debug(f"attempt={attempt} mode=text_json model={model_name} base_url={base_url}")
            result = text_agent.run_sync(json_prompt)
            payload = _extract_json_payload(result.output)
            guidance = LLMReportGuidance.model_validate_json(payload)
            if debug_enabled:
                _emit_debug(
                    f"live guidance ok attempt={attempt} mode=text_json summary_items={len(guidance.summary)} "
                    f"next_actions_items={len(guidance.next_actions)}"
                )
            return guidance
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if debug_enabled:
                _emit_debug(f"attempt={attempt} mode=text_json failed type={type(exc).__name__} detail={exc}")

    if debug_enabled and last_error is not None:
        _emit_debug(f"fallback=deterministic reason={type(last_error).__name__}")
    return None


def _extract_json_payload(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", stripped, flags=re.IGNORECASE | re.DOTALL)
    if fenced_match:
        return fenced_match.group(1)

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]

    raise ValueError("No JSON object found in model output")


def _is_tool_choice_auto_error(exc: Exception) -> bool:
    return "tool choice must be auto" in str(exc).lower()


def _model_requires_text_json_mode(model_name: str) -> bool:
    normalized = model_name.strip().lower()
    if normalized in _TOOL_CHOICE_AUTO_MODELS:
        return True

    additional = environ.get("POKECOACH_TOOL_CHOICE_AUTO_MODELS", "")
    if not additional.strip():
        return False

    configured = {item.strip().lower() for item in additional.split(",") if item.strip()}
    return normalized in configured


def _format_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _env_flag(values: Mapping[str, str], key: str) -> bool:
    return values.get(key, "").strip().lower() in _DEBUG_TRUTHY


def _emit_debug(message: str) -> None:
    print(f"[pokecoach.llm] {message}", file=sys.stderr)
