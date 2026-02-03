from __future__ import annotations

from typing import Dict

import pandas as pd

from market_report.domain.calculators.absorption import compute_absorption
from market_report.domain.calculators.inventory import compute_inventory
from market_report.domain.calculators.pricing import compute_pricing


class MetricsService:
    """Compute metrics from normalized tables."""

    def compute(self, tables: Dict[str, pd.DataFrame]) -> Dict[str, object]:
        metrics: Dict[str, object] = {}
        
        # Support both old table names and new historico_mercado table
        historico_table = tables.get("historico_mercado")
        inventory_table = tables.get("inventory") or historico_table
        pricing_table = tables.get("pricing") or historico_table
        absorption_table = tables.get("absorption") or historico_table

        if inventory_table is not None and not inventory_table.empty:
            metrics["inventory"] = compute_inventory(inventory_table)
        if pricing_table is not None and not pricing_table.empty:
            metrics["pricing"] = compute_pricing(pricing_table)
        if absorption_table is not None and not absorption_table.empty:
            metrics["absorption"] = compute_absorption(absorption_table)
        
        return metrics
