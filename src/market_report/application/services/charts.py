from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from market_report.config.schemas import ChartConfig
from market_report.ports.chart import ChartRenderer


class ChartsService:
    """Coordinate chart rendering."""

    def __init__(self, renderer: ChartRenderer):
        self._renderer = renderer

    def render(self, charts: list[ChartConfig], tables: Dict[str, pd.DataFrame], output_dir: Path) -> Dict[str, Path]:
        return self._renderer.render(charts, tables, output_dir)
