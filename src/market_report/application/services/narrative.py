from __future__ import annotations

from typing import Dict

from market_report.ports.narrative import NarrativeEngine


class NarrativeService:
    """Coordinate narrative generation."""

    def __init__(self, engine: NarrativeEngine):
        self._engine = engine

    def generate(self, metrics: Dict[str, object]) -> Dict[str, str]:
        return self._engine.generate(metrics)
