from __future__ import annotations

import pandas as pd


def compute_pricing(pricing_table: pd.DataFrame) -> dict:
    """Compute pricing KPIs from historico_mercado table.

    Calculates:
    - Average inventory price (Precio Promedio Inv.)
    - Average price per M2 ($M2 Promedio Inv)
    - Average M2 (M2 Promedio Inv)
    """
    if pricing_table.empty:
        return {
            "avg_inventory_price": None,
            "avg_price_per_m2": None,
            "avg_m2": None,
        }

    metrics = {}

    def weighted_avg(values, weights):
        values_num = pd.to_numeric(values, errors="coerce")
        weights_num = pd.to_numeric(weights, errors="coerce")
        valid_mask = values_num.notna() & weights_num.notna() & (weights_num > 0)
        if not valid_mask.any():
            return None
        weighted_sum = (values_num[valid_mask] * weights_num[valid_mask]).sum()
        weight_total = weights_num[valid_mask].sum()
        return float(weighted_sum / weight_total) if weight_total > 0 else None

    # Calculate average inventory price
    if "Precio Promedio Inv." in pricing_table.columns:
        if "Unidades Inventario" in pricing_table.columns:
            metrics["avg_inventory_price"] = weighted_avg(
                pricing_table["Precio Promedio Inv."], pricing_table["Unidades Inventario"]
            )
        else:
            price = pd.to_numeric(pricing_table["Precio Promedio Inv."], errors="coerce")
            metrics["avg_inventory_price"] = float(price.mean()) if price.notna().any() else None
    else:
        metrics["avg_inventory_price"] = None

    # Calculate average price per M2
    if "$M2 Promedio Inv" in pricing_table.columns:
        if "Unidades Inventario" in pricing_table.columns:
            metrics["avg_price_per_m2"] = weighted_avg(
                pricing_table["$M2 Promedio Inv"], pricing_table["Unidades Inventario"]
            )
        else:
            price_m2 = pd.to_numeric(pricing_table["$M2 Promedio Inv"], errors="coerce")
            metrics["avg_price_per_m2"] = float(price_m2.mean()) if price_m2.notna().any() else None
    else:
        metrics["avg_price_per_m2"] = None

    # Calculate average M2
    if "M2 Promedio Inv" in pricing_table.columns:
        if "Unidades Inventario" in pricing_table.columns:
            metrics["avg_m2"] = weighted_avg(
                pricing_table["M2 Promedio Inv"], pricing_table["Unidades Inventario"]
            )
        else:
            m2 = pd.to_numeric(pricing_table["M2 Promedio Inv"], errors="coerce")
            metrics["avg_m2"] = float(m2.mean()) if m2.notna().any() else None
    else:
        metrics["avg_m2"] = None

    return metrics
