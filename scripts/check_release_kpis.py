#!/usr/bin/env python3
"""Deterministic Phase 5 KPI gate checker."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pokecoach.quality_kpis import evaluate_release_kpis


def main() -> int:
    result = evaluate_release_kpis()
    payload = asdict(result)

    checks = {
        "hallucination_rate": result.hallucination_rate == 0.0,
        "evidence_coverage": result.evidence_coverage == 1.0,
        "golden_stability": result.golden_stability == 1.0,
    }

    payload["checks"] = checks
    print(json.dumps(payload, indent=2, sort_keys=True))

    if all(checks.values()):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
