# Repository Guidelines

## Project Overview

**PokeCoach** is an evidence-first post-game coach for Pokémon TCG Live.

Current implementation status:
- Typed contracts in `src/pokecoach/schemas.py` (including `match_facts` and `play_bundles`).
- Deterministic tools in `src/pokecoach/tools.py`:
  - `index_turns(log_text) -> list[TurnSpan]`
  - `find_key_events(log_text) -> KeyEventIndex`
  - `compute_basic_stats(log_text) -> MatchStats`
  - `extract_turn_summary(turn_span, log_text) -> TurnSummary`
  - `extract_match_facts(log_text) -> MatchFacts`
  - `extract_play_bundles(log_text) -> list[PlayBundle]`
- Report pipeline in `src/pokecoach/report.py`:
  - `generate_post_game_report(log_text) -> PostGameReport`
  - deterministic impact scoring for turning points
  - fact-only summary enforcement for Spanish logs
- Integrity/guardrails modules:
  - `src/pokecoach/guardrails.py`
  - `src/pokecoach/summary_integrity.py`
- Optional LLM guidance via OpenRouter in `src/pokecoach/llm_provider.py` with capability-aware fallback routing.
- Release KPI checks in `src/pokecoach/quality_kpis.py` and `scripts/check_release_kpis.py`.
- Spec contract in `docs/spec_v1.md`.
- Sample logs in `logs_prueba/` for local deterministic validation.

Core non-negotiables:
- **Evidence or it didn’t happen**.
- `TurningPoint` and `Mistake` must carry `EvidenceSpan`.
- Hidden information must be explicit in `unknowns`.
- Parser behavior is deterministic and fail-open.
- Initial inference provider is **OpenRouter** (configurable by env, not hardcoded in business logic).

---

## Build & Test Commands

### Setup
```bash
uv sync --all-groups
```

### Lint & Format
```bash
uv run ruff check .
uv run ruff format --check .
# optional autofix
uv run ruff format .
uv run ruff check . --fix
```

### Tests
```bash
uv run pytest -q
# single file
uv run pytest tests/test_index_turns.py -q
```

---

## Project Structure

```text
.
├── docs/
│   ├── spec_v1.md
│   ├── release_checklist_phase5.md
│   └── adr_cli_framework.md
├── src/
│   └── pokecoach/
│       ├── __init__.py
│       ├── schemas.py
│       ├── tools.py
│       ├── report.py
│       ├── guardrails.py
│       ├── summary_integrity.py
│       ├── llm_provider.py
│       ├── quality_kpis.py
│       └── events/registry.py
├── scripts/
│   └── check_release_kpis.py
├── tests/
│   ├── test_schemas.py
│   ├── test_index_turns.py
│   ├── test_find_key_events.py
│   ├── test_compute_basic_stats.py
│   ├── test_match_facts.py
│   ├── test_play_bundles.py
│   ├── test_release_kpis.py
│   └── test_report_pipeline.py
├── logs_prueba/
├── ROADMAP.md
└── pyproject.toml
```

Notes:
- `Idea_inicial.md` is intentionally ignored for commit hygiene.
- `logs_prueba/` is used for local deterministic validation; avoid adding sensitive/raw personal logs.
- Keep implementation code under `src/pokecoach/` only.

---

## Coding Standards

- Code/docs/comments in repository implementation must be in **English**.
- Python `>=3.12`.
- Type hints required for public APIs.
- Use Pydantic models for typed contracts and validation boundaries.
- Keep parsing logic deterministic (regex/state-machine style), not LLM-dependent.
- Prefer small pure functions and explicit return types.

---

## Testing Standards

- Framework: `pytest`.
- Add tests for every parser/report behavior change.
- Cover edge cases seen in `logs_prueba/`, especially:
  - `Turno de [playerName]` placeholder headers.
  - `Chequeo Pokémon` inter-turn blocks.
  - Compound event lines/blocks (attack + weakness + KO + prizes).
- Minimum gates before commit:
  - `ruff check .`
  - `ruff format --check .`
  - `pytest -q`

---

## Commit & PR Rules

Use Conventional Commits:
- `feat:` new behavior
- `fix:` bug fix
- `docs:` documentation/spec changes
- `chore:` maintenance/tooling

PRs should include:
- what changed and why,
- test evidence,
- impact on evidence policy/unknowns behavior when relevant.

Keep PRs focused and small.
