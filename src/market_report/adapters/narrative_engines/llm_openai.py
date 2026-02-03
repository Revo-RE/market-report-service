from __future__ import annotations

from typing import Dict

from market_report.ports.narrative import NarrativeEngine


class OpenAiNarrativeEngine(NarrativeEngine):
    """Premium adapter stub for OpenAI narrative generation."""

    def generate(self, metrics: Dict[str, object]) -> Dict[str, str]:
        raise NotImplementedError("TODO: Implement OpenAI narrative generation.")
