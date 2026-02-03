from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

import pandas as pd


class DataSource(ABC):
    """Port for data ingestion."""

    @abstractmethod
    def load(self) -> Dict[str, pd.DataFrame]:
        """Return raw tables keyed by tab name."""
        raise NotImplementedError
