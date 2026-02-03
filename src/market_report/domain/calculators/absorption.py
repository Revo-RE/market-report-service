from __future__ import annotations

import pandas as pd


def compute_absorption(absorption_table: pd.DataFrame) -> dict:
    """Compute absorption KPIs from historico_mercado table.

    Calculates:
    - Total absorption by project (Absorción por Proyecto)
    - Average absorption
    - Absorption by quarter
    """
    if absorption_table.empty:
        return {
            "total_absorption": 0,
            "avg_absorption": 0.0,
            "absorption_by_quarter": {},
        }

    metrics = {}

    # Calculate total absorption
    if "Absorción por Proyecto" in absorption_table.columns:
        absorption = pd.to_numeric(absorption_table["Absorción por Proyecto"], errors="coerce")
        metrics["total_absorption"] = int(absorption.sum()) if absorption.notna().any() else 0
        metrics["avg_absorption"] = float(absorption.mean()) if absorption.notna().any() else 0.0

        # Calculate absorption by quarter
        if "Último Trimestre" in absorption_table.columns:
            quarter_absorption = (
                absorption_table.groupby("Último Trimestre")["Absorción por Proyecto"]
                .apply(lambda x: pd.to_numeric(x, errors="coerce").sum())
                .to_dict()
            )
            metrics["absorption_by_quarter"] = {str(k): int(v) for k, v in quarter_absorption.items() if pd.notna(v)}
    else:
        metrics["total_absorption"] = 0
        metrics["avg_absorption"] = 0.0
        metrics["absorption_by_quarter"] = {}

    return metrics
