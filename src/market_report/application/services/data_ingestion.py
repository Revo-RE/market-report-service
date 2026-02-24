from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, List

import pandas as pd


@dataclass
class DataIngestionService:
    """Load and normalize quarterly Excel files into a canonical table."""

    def load_quarterly_data(self, raw_tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        raw = raw_tables.get("raw", pd.DataFrame())
        if raw.empty:
            return raw
        raw = raw.copy()
        raw = raw.dropna(subset=["Proyecto", "Último Trimestre"])
        return raw

    def compute_display_start(self, display_start: str, lookback_quarters: int = 2) -> str:
        year, quarter = self._parse_quarter(display_start)
        total = year * 4 + (quarter - 1)
        total -= lookback_quarters
        new_year = total // 4
        new_quarter = (total % 4) + 1
        return f"{new_year} - Q{new_quarter}"

    def filter_display_window(self, historico: pd.DataFrame, display_start: str) -> pd.DataFrame:
        if historico.empty:
            return historico
        start_key = self._quarter_key(display_start)
        historico = historico.copy()
        historico["_qkey"] = historico["Trimestre"].map(self._quarter_key)
        historico = historico.loc[historico["_qkey"] >= start_key]
        return historico.drop(columns=["_qkey"], errors="ignore").reset_index(drop=True)

    def _parse_quarter(self, value: str) -> tuple[int, int]:
        match = re.search(r"(\d{4})\s*-\s*Q(\d)", str(value))
        if not match:
            raise ValueError(f"Invalid quarter format: {value}")
        return int(match.group(1)), int(match.group(2))

    def _quarter_key(self, value: str) -> tuple[int, int]:
        year, q = self._parse_quarter(value)
        return (year, q)
