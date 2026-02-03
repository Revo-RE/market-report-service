from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd

from market_report.config.schemas import ExcelFolderConfig
from market_report.ports.data_source import DataSource


class LocalExcelFolderDataSource(DataSource):
    """Load and concatenate local Excel files from a folder."""

    def __init__(self, config: ExcelFolderConfig):
        self._config = config

    def load(self) -> Dict[str, pd.DataFrame]:
        folder = Path(self._config.path)
        if not folder.exists():
            raise FileNotFoundError(f"Excel folder not found: {folder}")
        files = sorted(folder.glob(self._config.pattern))
        if not files:
            raise FileNotFoundError(f"No Excel files found in {folder} with pattern {self._config.pattern}")
        frames: List[pd.DataFrame] = []
        for path in files:
            frame = pd.read_excel(path, sheet_name=self._config.sheet_name)
            frames.append(frame)
        combined = pd.concat(frames, ignore_index=True)
        return {self._config.table_key: combined}
