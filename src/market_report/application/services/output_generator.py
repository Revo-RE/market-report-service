from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd


@dataclass
class OutputGeneratorService:
    """Generate minimal 3-sheet output structure."""

    def build_tabs(self, ids: pd.DataFrame, historico: pd.DataFrame, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return {
            "Ids": ids,
            "Historico": historico,
            "Data": data,
        }
