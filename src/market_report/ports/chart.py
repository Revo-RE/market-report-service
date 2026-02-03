from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict

import pandas as pd

from market_report.config.schemas import ChartConfig


class ChartRenderer(ABC):
    """Port for rendering charts."""

    @abstractmethod
    def render(self, charts: list[ChartConfig], tables: Dict[str, pd.DataFrame], output_dir: Path) -> Dict[str, Path]:
        """Render charts and return file paths keyed by chart name."""
        raise NotImplementedError
