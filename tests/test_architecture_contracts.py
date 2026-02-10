from __future__ import annotations

import ast
from pathlib import Path

from pokecoach.events.registry import EVENT_DETECTORS
from pokecoach.schemas import KeyEvent


def test_event_registry_exposes_callable_detectors() -> None:
    assert EVENT_DETECTORS, "EVENT_DETECTORS must not be empty"

    for detector in EVENT_DETECTORS:
        assert callable(detector), f"Detector must be callable: {detector!r}"
        result = detector("X infligió 10 puntos de daño usando Y.", 1, "raw")
        assert isinstance(result, list), "Detector must return list[KeyEvent]"
        assert all(isinstance(item, KeyEvent) for item in result)


def test_tools_iter_events_uses_event_registry() -> None:
    tools_source = Path("src/pokecoach/tools.py").read_text(encoding="utf-8")
    module = ast.parse(tools_source)

    iter_events = next(
        node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "_iter_events"
    )
    iter_source = ast.get_source_segment(tools_source, iter_events) or ""

    assert "for detector in EVENT_DETECTORS" in iter_source


def test_report_module_stays_as_facade_without_guardrail_impl_details() -> None:
    report_source = Path("src/pokecoach/report.py").read_text(encoding="utf-8")

    assert "from pokecoach.guardrails import apply_report_guardrails" in report_source
    assert "def _apply_report_guardrails" not in report_source
