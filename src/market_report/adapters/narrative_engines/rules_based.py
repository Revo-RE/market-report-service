from __future__ import annotations

from typing import Dict

from market_report.ports.narrative import NarrativeEngine


class RulesBasedNarrativeEngine(NarrativeEngine):
    """Light narrative engine using simple rules.

    TODO: Expand rule coverage for slide-level insights.
    """

    def generate(self, metrics: Dict[str, object]) -> Dict[str, str]:
        return {
            "overview": f"Total units: {metrics.get('inventory', {}).get('total_units', 0)}"
        }
