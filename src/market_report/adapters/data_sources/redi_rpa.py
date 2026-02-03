from __future__ import annotations

from typing import Dict

import pandas as pd

from market_report.ports.data_source import DataSource


class RediRpaDataSource(DataSource):
    """Premium adapter stub for RPA-based Redi extraction."""

    def load(self) -> Dict[str, pd.DataFrame]:
        raise NotImplementedError("TODO: Implement RPA-based data extraction.")
