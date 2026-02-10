# Repository Guidelines

## Project Overview

**PokeCoach** is an evidence-first post-game coach for Pokémon TCG Live.

Current implementation status:
- Typed contracts in `src/pokecoach/schemas.py`.
- Deterministic tools in `src/pokecoach/tools.py`:
  - `index_turns(log_text) -> list[TurnSpan]`
  - `find_key_events(log_text) -> KeyEventIndex`
  - `compute_basic_stats(log_text) -> MatchStats`
  - `extract_turn_summary(turn_span, log_text) -> TurnSummary`
- Initial report assembly in `src/pokecoach/report.py`:
  - `generate_post_game_report(log_text) -> PostGameReport`
- Spec contract in `docs/spec_v1.md`.
- Sample logs in `logs_prueba/` (Spanish, with and without card IDs).

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
│   └── spec_v1.md
├── src/
│   └── pokecoach/
│       ├── __init__.py
│       ├── schemas.py
│       ├── tools.py
│       └── report.py
├── tests/
│   ├── test_schemas.py
│   ├── test_index_turns.py
│   ├── test_find_key_events.py
│   ├── test_compute_basic_stats.py
│   └── test_report_pipeline.py
├── logs_prueba/
├── ROADMAP.md
└── pyproject.toml
```

Notes:
- `Idea_inicial.md` and `logs_prueba/` are intentionally ignored for commit hygiene.
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
