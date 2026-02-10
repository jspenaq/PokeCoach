# PokeCoach

Evidence-first post-game coach for **Pokémon TCG Live**.

PokeCoach converts noisy battle logs into a typed, auditable `PostGameReport` with anti-hallucination guardrails:
- actionable claims require evidence,
- low-confidence claims are rerouted to `unknowns`,
- hidden information is explicitly surfaced.

## Current Status

Implemented:
- Typed contracts (`src/pokecoach/schemas.py`), including deterministic `match_facts` and `play_bundles`.
- Deterministic tools (`src/pokecoach/tools.py`):
  - `index_turns`
  - `find_key_events`
  - `compute_basic_stats`
  - `extract_turn_summary`
  - `extract_match_facts`
  - `extract_play_bundles`
- Report assembly pipeline (`src/pokecoach/report.py`):
  - `generate_post_game_report(log_text)`
  - impact-ranked turning points
  - fact-only Spanish summary enforcement
- Guardrail/integrity modules:
  - `src/pokecoach/guardrails.py`
  - `src/pokecoach/summary_integrity.py`
- OpenRouter-backed optional guidance (`src/pokecoach/llm_provider.py`) with model-capability routing and deterministic fallback.
- Release KPI checker (`src/pokecoach/quality_kpis.py`, `scripts/check_release_kpis.py`).
- Technical contract spec (`docs/spec_v1.md`).

## Project Structure

```text
src/pokecoach/
  schemas.py
  tools.py
  report.py
  guardrails.py
  summary_integrity.py
  llm_provider.py
  quality_kpis.py
  events/registry.py
scripts/
  check_release_kpis.py
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

## CI

GitHub Actions runs lint and tests on pushes and pull requests to `main` using `.github/workflows/ci.yml`.

Optional badge (replace `<owner>` and `<repo>`):

```md
![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)
```

## Quick Example

```python
from pathlib import Path

from pokecoach.report import generate_post_game_report

log_text = Path("logs_prueba/battle_logs_ptcgl_spanish_con_ids_7.txt").read_text(encoding="utf-8")
report = generate_post_game_report(log_text)

print(report.model_dump_json(indent=2))
```

`PostGameReport` includes `match_facts`, a deterministic snapshot of observable outcomes:
- `winner`
- `went_first_player`
- `turns_count`
- `observable_prizes_taken_by_player`
- `kos_by_player`
- `concede`

These facts are rendered in CLI Markdown as a scoreboard section and are kept consistent with summary fact lines in deterministic mode.

## CLI Usage

Generate report to stdout (JSON default):

```bash
uv run python run_report.py logs_prueba/battle_logs_9_feb_2026_spanish_con_ids_1.txt
```

Generate Markdown to stdout:

```bash
uv run python run_report.py logs_prueba/battle_logs_9_feb_2026_spanish_con_ids_1.txt --format md
```

Example Markdown snippet:

```md
## Match Facts

| Fact | Value |
| --- | --- |
| Winner | Kami-Yan |
| Went first | XueDii |
| Turns | 12 |
| Concede detected | Yes |

### Scoreboard

| Player | Observable Prizes | KOs |
| --- | ---: | ---: |
| Kami-Yan | 6 | 4 |
| XueDii | 4 | 3 |
```

Write output to file:

```bash
uv run python run_report.py logs_prueba/battle_logs_9_feb_2026_spanish_con_ids_1.txt --output reports/report.json
```

Force deterministic path (skip LLM guidance):

```bash
uv run python run_report.py logs_prueba/battle_logs_9_feb_2026_spanish_con_ids_1.txt --deterministic-only
```

CLI troubleshooting:
- Missing input file: the CLI exits non-zero and prints `error: Log file not found: <path>` to stderr.
- Deterministic-only mode: use `--deterministic-only` to bypass LLM guidance and force deterministic fallback output.
- Output path creation: when using `--output`, parent directories are created automatically if they do not exist.

## PydanticAI Runtime (OpenRouter-first)

```bash
uv run python examples/pydanticai_poc.py
```

Optional live model path (OpenRouter):

```bash
export OPENROUTER_API_KEY="your_key"
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
export POKECOACH_PYDANTICAI_MODEL="openai/gpt-4o-mini"
uv run python examples/pydanticai_poc.py
```

Model compatibility routing (runtime):
- Structured output path is used by default.
- If a provider/model requires `tool_choice=auto` semantics, PokeCoach can route to a text+JSON validation path and then validate locally with Pydantic.
- Deterministic fallback remains the safety net when live guidance fails.

Useful debug flags:

```bash
export POKECOACH_LLM_DEBUG=1
# optional comma-separated list for forced text+json mode
export POKECOACH_TOOL_CHOICE_AUTO_MODELS="z-ai/glm-4.5-air:free"
```

## License

MIT — see [LICENSE](./LICENSE).
