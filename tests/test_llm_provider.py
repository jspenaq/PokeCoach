from __future__ import annotations

from pokecoach.llm_provider import (
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_PYDANTICAI_MODEL,
    LLMReportGuidance,
    PydanticAIRuntimeConfig,
    load_runtime_config,
    maybe_generate_guidance,
)


def test_load_runtime_config_defaults() -> None:
    config = load_runtime_config({})
    assert config.openrouter_api_key is None
    assert config.openrouter_base_url == DEFAULT_OPENROUTER_BASE_URL
    assert config.model == DEFAULT_PYDANTICAI_MODEL
    assert config.live_mode_enabled is False


def test_load_runtime_config_from_environment_values() -> None:
    config = load_runtime_config(
        {
            "OPENROUTER_API_KEY": "test-key",
            "OPENROUTER_BASE_URL": "https://example.test/v1",
            "POKECOACH_PYDANTICAI_MODEL": "openai/gpt-4o-mini",
        }
    )
    assert config.openrouter_api_key == "test-key"
    assert config.openrouter_base_url == "https://example.test/v1"
    assert config.model == "openai/gpt-4o-mini"
    assert config.live_mode_enabled is True


def test_maybe_generate_guidance_returns_none_when_live_mode_disabled() -> None:
    config = PydanticAIRuntimeConfig(
        openrouter_api_key=None,
        openrouter_base_url=DEFAULT_OPENROUTER_BASE_URL,
        model=DEFAULT_PYDANTICAI_MODEL,
    )
    result = maybe_generate_guidance(
        log_text="Turn 1",
        fallback_summary=["a", "b", "c", "d", "e"],
        fallback_next_actions=["x", "y", "z"],
        config=config,
    )
    assert result is None


def test_llm_report_guidance_schema_bounds() -> None:
    guidance = LLMReportGuidance(
        summary=["s1", "s2", "s3", "s4", "s5"],
        next_actions=["n1", "n2", "n3"],
    )
    assert len(guidance.summary) == 5
    assert len(guidance.next_actions) == 3
