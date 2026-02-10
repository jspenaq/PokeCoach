# PokeCoach

Evidence-first post-game coach for **Pokémon TCG Live**.

PokeCoach converts noisy battle logs into a typed, auditable `PostGameReport` with anti-hallucination guardrails:
- actionable claims require evidence,
- low-confidence claims are rerouted to `unknowns`,
- hidden information is explicitly surfaced.

## Current Status

Implemented:
- Typed contracts (`src/pokecoach/schemas.py`)
- Deterministic tools (`src/pokecoach/tools.py`):
  - `index_turns`
  - `find_key_events`
  - `compute_basic_stats`
  - `extract_turn_summary`
- Initial report assembly (`src/pokecoach/report.py`):
  - `generate_post_game_report(log_text)`
- Guardrails for evidence + confidence (`tests/test_report_guardrails.py`)
- Technical contract spec (`docs/spec_v1.md`)

## Project Structure

```text
src/pokecoach/
  schemas.py
  tools.py
  report.py
tests/
logs_prueba/
docs/spec_v1.md
```

## Setup

```bash
uv sync --all-groups
```

## Quality Gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

## Quick Example

```python
from pathlib import Path

from pokecoach.report import generate_post_game_report

log_text = Path("logs_prueba/battle_logs_9_feb_2026_spanish.txt").read_text(encoding="utf-8")
report = generate_post_game_report(log_text)

print(report.model_dump_json(indent=2))
```

## PoC (pydantic + pydantic-ai)

```bash
uv run python examples/pydanticai_poc.py
```

Optional real model path:

```bash
export OPENAI_API_KEY="your_key"
export POKECOACH_PYDANTICAI_MODEL="openai:gpt-4o-mini"
uv run python examples/pydanticai_poc.py
```

## License

MIT — see [LICENSE](./LICENSE).
