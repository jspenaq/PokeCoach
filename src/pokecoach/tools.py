"""Deterministic tool interfaces for upcoming parser implementation.

NOTE: Signatures are defined in spec_v1. Implementations are pending.
"""

from __future__ import annotations

from typing import Any


def index_turns(log_text: str) -> list[Any]:
    raise NotImplementedError


def find_key_events(log_text: str) -> Any:
    raise NotImplementedError


def extract_turn_summary(turn_span: Any, log_text: str) -> Any:
    raise NotImplementedError


def compute_basic_stats(log_text: str) -> Any:
    raise NotImplementedError
