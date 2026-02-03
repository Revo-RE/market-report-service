from __future__ import annotations

from typing import Dict

import pandas as pd

from market_report.ports.data_source import DataSource


class RediExportDataSource(DataSource):
    """Premium adapter stub for Redi export endpoints."""

    def load(self) -> Dict[str, pd.DataFrame]:
        raise NotImplementedError("TODO: Implement Redi export ingestion.")
