# ADR: CLI Framework Choice (v1)

## Status
Accepted (2026-02-10)

## Context
PokeCoach needs a production-ready CLI for a small command surface in v1:
- `run_report.py <log_path>`
- `--format {json,md}`
- `--output <path>`
- `--deterministic-only`

We want low operational risk, minimal dependencies, and straightforward maintenance.

## Decision
Use `argparse` for v1 CLI implementation.

## Consequences
### Positive
- No extra runtime dependency.
- Stable, standard library behavior.
- Good enough UX for current command surface.
- Easy CI/CD and packaging footprint.

### Negative
- More boilerplate than Typer/Click.
- Lower DX if CLI grows significantly.

## Migration Trigger (v2)
Re-evaluate and likely migrate to **Typer** when any of these are true:
1. More than 3 top-level subcommands are required.
2. We need shell autocompletion/command groups with richer UX.
3. CLI argument schemas become difficult to maintain in `argparse`.

## Notes
This ADR preserves SOLID by keeping CLI parsing thin and delegating business logic to the report pipeline modules.
