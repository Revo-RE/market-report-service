from __future__ import annotations

from typing import Dict

import pandas as pd

from market_report.config.schemas import TableConfig


class TransformService:
    """Normalize raw data into canonical tables."""

    def normalize(self, raw_tables: Dict[str, pd.DataFrame], table_configs: list[TableConfig]) -> Dict[str, pd.DataFrame]:
        normalized: Dict[str, pd.DataFrame] = {}
        for table in table_configs:
            if table.derived_from:
                continue
            raw = raw_tables.get(table.source_tab)
            if raw is None:
                normalized[table.name] = pd.DataFrame()
                continue
            
            # If column_mappings is empty and retain_all_columns is True, keep all columns as-is
            if not table.column_mappings and table.retain_all_columns:
                normalized[table.name] = raw.copy()
            elif table.column_mappings:
                renamed = raw.rename(columns={v: k for k, v in table.column_mappings.items()})
                if table.retain_all_columns:
                    normalized[table.name] = renamed.copy()
                else:
                    normalized[table.name] = renamed.reindex(columns=list(table.column_mappings.keys())).copy()
            else:
                # No mappings and not retaining all - use raw as-is
                normalized[table.name] = raw.copy()

        for table in table_configs:
            if not table.derived_from:
                continue
            base = normalized.get(table.derived_from, pd.DataFrame()).copy()
            if base.empty:
                normalized[table.name] = base
                continue
            if table.order_by and table.order_by_kind == "quarter":
                base = base.copy()
                base["__order_key__"] = base[table.order_by].apply(self._quarter_key)
                base = base.sort_values(by="__order_key__", ascending=True).drop(columns="__order_key__")
            if table.order_by and not table.order_by_kind:
                base = base.sort_values(by=table.order_by, ascending=True)
            if table.group_by:
                # For proyectos nuevos, we want the first appearance of each project
                # Sort by quarter first to ensure we get the earliest quarter
                if table.order_by and table.order_by_kind == "quarter":
                    # Already sorted by quarter above
                    base = base.drop_duplicates(subset=table.group_by, keep="first")
                else:
                    base = base.drop_duplicates(subset=table.group_by, keep="first")
            if table.column_mappings and not table.retain_all_columns:
                base = base.reindex(columns=list(table.column_mappings.keys()))
            normalized[table.name] = base.reset_index(drop=True)
        return normalized

    def compute_display_start_quarter(self, table: pd.DataFrame, quarter_column: str) -> str | None:
        if table.empty or quarter_column not in table.columns:
            return None
        quarters = (
            table[quarter_column]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        if len(quarters) < 3:
            return None
        quarters_sorted = sorted(quarters, key=self._quarter_key)
        return quarters_sorted[2]

    def apply_quarter_window(self, table: pd.DataFrame, quarter_column: str, display_start: str | None) -> pd.DataFrame:
        if table.empty or not display_start or quarter_column not in table.columns:
            return table
        start_key = self._quarter_key(display_start)
        quarter_values = table[quarter_column]
        quarter_keys = quarter_values.apply(self._quarter_key)
        mask = quarter_values.isna() | (quarter_keys >= start_key)
        return table.loc[mask].copy()

    @staticmethod
    def _quarter_key(value: object) -> tuple[int, int]:
        if not isinstance(value, str):
            return (9999, 9)
        parts = value.split("-")
        if len(parts) != 2:
            return (9999, 9)
        year_raw, quarter_raw = parts
        try:
            year = int(year_raw.strip())
            quarter = int(quarter_raw.strip().replace("Q", ""))
        except ValueError:
            return (9999, 9)
        return (year, quarter)
