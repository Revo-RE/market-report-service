from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd

from market_report.config.schemas import ChartConfig
from market_report.ports.chart import ChartRenderer


class MatplotlibChartRenderer(ChartRenderer):
    """Render charts with matplotlib."""

    def render(self, charts: list[ChartConfig], tables: Dict[str, pd.DataFrame], output_dir: Path) -> Dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        paths: Dict[str, Path] = {}
        for chart in charts:
            table = tables.get(chart.table, pd.DataFrame())
            path = output_dir / chart.output
            self._render_chart(chart, table, path)
            paths[chart.name] = path
        return paths

    def _render_chart(self, chart: ChartConfig, table: pd.DataFrame, output_path: Path) -> None:
        plt.figure(figsize=(8, 4.5))
        if table.empty:
            plt.text(0.5, 0.5, "No data", ha="center", va="center")
        else:
            grouped = self._aggregate(table, chart)
            if chart.chart_type == "line":
                plt.plot(grouped[chart.x], grouped[chart.y], marker="o")
            else:
                plt.bar(grouped[chart.x].astype(str), grouped[chart.y])
            plt.xlabel(chart.x)
            plt.ylabel(chart.y)
            plt.title(chart.name)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()

    def _aggregate(self, table: pd.DataFrame, chart: ChartConfig) -> pd.DataFrame:
        if chart.aggregate == "count":
            grouped = table.groupby(chart.x, dropna=False)[chart.y].count().reset_index()
            grouped.rename(columns={chart.y: chart.y}, inplace=True)
            return grouped
        if chart.aggregate == "sum":
            return table.groupby(chart.x, dropna=False)[chart.y].sum().reset_index()
        return table[[chart.x, chart.y]].copy()
