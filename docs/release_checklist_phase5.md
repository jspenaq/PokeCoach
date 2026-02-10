# Release Checklist (Phase 5)

This checklist is the release gate for quality guardrails defined in `ROADMAP.md` Fase 5.

## KPI thresholds (must pass)

- Hallucination rate: **0.0%**
  - Definition: actionable claims (`turning_points` + `mistakes`) without non-empty evidence.
  - Deterministic check: `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/check_release_kpis.py`
- Evidence coverage: **100%**
  - Definition: actionable claims carrying non-empty evidence spans.
  - Deterministic check: `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/check_release_kpis.py`
- Golden stability: **100%**
  - Definition: all expected minimum baselines in `tests/golden/expected_minimums.json` pass.
  - Deterministic check: `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/check_release_kpis.py`
- CI green: **required**
  - Definition: lint + formatting + tests all pass.
  - Deterministic checks:
    - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
    - `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check .`
    - `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q`

## Focused golden coverage for ambiguous/compound parsing

- `tests/golden/fixtures/ambiguous_turns_interturn_block.txt`
  - Covers placeholder turn headers plus inter-turn `Chequeo Pokémon` style blocks.
- `tests/golden/fixtures/compound_single_line_events.txt`
  - Covers single-line compound extraction (attack + KO + prizes) and event co-occurrence.

## Pass/Fail rule

Release is blocked if any KPI check above fails.
