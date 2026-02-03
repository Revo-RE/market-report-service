from __future__ import annotations

import pandas as pd


def compute_inventory(inventory_table: pd.DataFrame) -> dict:
    """Compute inventory KPIs from historico_mercado table.

    Calculates:
    - Total units (Unidades Totales)
    - Inventory units (Unidades Inventario)
    - Months of inventory (Meses de Inventario)
    - Months in market (Meses en el Mercado)
    """
    if inventory_table.empty:
        return {
            "total_units": 0,
            "inventory_units": 0,
            "avg_months_inventory": 0.0,
            "avg_months_in_market": 0.0,
        }

    metrics = {"total_units": 0, "inventory_units": 0}

    def weighted_avg(values, weights):
        values_num = pd.to_numeric(values, errors="coerce")
        weights_num = pd.to_numeric(weights, errors="coerce")
        valid_mask = values_num.notna() & weights_num.notna() & (weights_num > 0)
        if not valid_mask.any():
            return 0.0
        weighted_sum = (values_num[valid_mask] * weights_num[valid_mask]).sum()
        weight_total = weights_num[valid_mask].sum()
        return float(weighted_sum / weight_total) if weight_total > 0 else 0.0

    # Calculate total units
    if "Unidades Totales" in inventory_table.columns:
        metrics["total_units"] = int(pd.to_numeric(inventory_table["Unidades Totales"], errors="coerce").sum())

    # Calculate inventory units
    if "Unidades Inventario" in inventory_table.columns:
        metrics["inventory_units"] = int(pd.to_numeric(inventory_table["Unidades Inventario"], errors="coerce").sum())

    # Calculate average months of inventory
    if "Meses de Inventario" in inventory_table.columns:
        if "Unidades Inventario" in inventory_table.columns:
            metrics["avg_months_inventory"] = weighted_avg(
                inventory_table["Meses de Inventario"], inventory_table["Unidades Inventario"]
            )
        else:
            months_inv = pd.to_numeric(inventory_table["Meses de Inventario"], errors="coerce")
            metrics["avg_months_inventory"] = float(months_inv.mean()) if months_inv.notna().any() else 0.0

    # Calculate average months in market
    if "Meses en el Mercado" in inventory_table.columns:
        months_market = pd.to_numeric(inventory_table["Meses en el Mercado"], errors="coerce")
        metrics["avg_months_in_market"] = float(months_market.mean()) if months_market.notna().any() else 0.0

    return metrics
