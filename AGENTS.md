# Repository Guidelines

## Project Overview

**PokeCoach** is an evidence-based, tool-driven agentic AI system that converts noisy battle logs from Pokémon Trading Card Game Live into actionable coaching reports.

The system parses Spanish-language battle logs (with or without card IDs) and generates a typed `PostGameReport` (Pydantic) containing:
- Match summary and turning points
- Potential misplays with confidence scoring
- Explicit unknowns (hidden information like hand, prizes, opponent deck)
- Actionable next steps for improvement

**Core principles:**
- **Anti-hallucination design**: Every claim requires an `EvidenceSpan` (line ranges from the log). No evidence = no claim.
- **Tool-driven architecture**: Deterministic parsing tools (regex + lightweight state machine) extract turns, key events (KOs, prizes, attacks, supporters/stadiums), and stats. The agent composes these outputs into reports.
- **Fail-open behavior**: Unparsed segments are preserved as RAW evidence to maintain robustness across log format variations.
- **Uncertainty as a feature**: Hidden information is explicitly marked rather than guessed.

The MVP targets competitive players who want to learn from their games without manual log review, delivering coaching that's fast, auditable, and grounded in observable evidence using LLMs.

## Build & Test Commands

### Development Setup
```bash
# Install dependencies
uv sync
```

### Linting & Formatting
```bash
# Format code (auto-fix)
uv run ruff format pokecoach/

# Lint code (auto-fix)
uv run ruff check pokecoach/ --fix

# Lint without fixing (CI mode)
uv run ruff check pokecoach/
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_auth.py

# Run single test function
uv run pytest tests/test_auth.py::test_signup_success

# Run with verbose output
uv run pytest -v

# Run async tests only
uv run pytest -m asyncio
```

## Project Structure & Module Organization
This repository is an early-stage Python project.
- `pyproject.toml`: project metadata and Python requirement (`>=3.12`).
- `README.md`: top-level project overview (currently minimal).
- `Idea_inicial.md`: product/feature notes.
- `logs_prueba/`: sample battle-log inputs used for exploration and parsing tests.

When adding code, use a `src/` layout (for example `src/pokecoach/`) and mirror tests under `tests/` (for example `tests/test_parser.py`). Keep raw input files in dedicated data folders and avoid mixing them with source modules.

## Coding Style & Naming Conventions
- **Write all code in English**: variable names, function names, comments, docstrings, and documentation must be in English. (Battle logs are in Spanish, but the codebase is English-only.)
- Follow PEP 8 with 4-space indentation.
- Use type hints for public functions and dataclasses/models.
- Modules/files: `snake_case.py`; classes: `PascalCase`; functions/variables: `snake_case`; constants: `UPPER_SNAKE_CASE`.
- Prefer small, single-purpose modules (e.g., `parser.py`, `battle_analyzer.py`).

Format and lint consistently; if adding tools, standardize via `pyproject.toml`.

## Testing Guidelines
Use `pytest`.
- Test files: `tests/test_<unit>.py`.
- Test names: `test_<behavior>()`.
- Cover parsing edge cases using fixtures derived from `logs_prueba/`.
- Add regression tests for every bug fix.

Target meaningful coverage on core logic (parsing, decision support, and data transformations), not only happy paths.

## Commit & Pull Request Guidelines
There is no existing commit history yet; adopt Conventional Commits from now on:
- `feat: add battle log parser`
- `fix: handle missing move identifiers`
- `docs: update repository guidelines`

PRs should include:
- clear summary of behavior changes,
- linked issue/context,
- test evidence (`pytest` output),
- sample input/output when parser behavior changes.

Keep PRs focused and small enough for quick review.
