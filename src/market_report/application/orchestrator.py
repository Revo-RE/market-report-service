from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import pandas as pd

from market_report.application.services.data_ingestion import DataIngestionService
from market_report.application.services.output_generator import OutputGeneratorService
from market_report.application.services.calculation_engine import CalculationEngineService
from market_report.domain.entities.consolidated_data import ConsolidatedData


@dataclass
class ConsolidationResult:
    output_path: Path | None
    projects_count: int
    quarters_count: int
    sheets: Dict[str, pd.DataFrame]


class ConsolidationOrchestrator:
    """Orchestrate the minimal consolidation pipeline."""

    def __init__(self):
        self.ingestion = DataIngestionService()
        self.generator = OutputGeneratorService()
        self.calculation = CalculationEngineService()

    def execute(
        self,
        raw_tables: Dict[str, pd.DataFrame],
        layout_path: str | None,
        layout_override: Dict[str, list[str]] | None,
        start_quarter: str | None,
        display_start_quarter: str | None,
        filter_path: str | None = None,
    ) -> ConsolidationResult:
        raw_clean = self.ingestion.load_quarterly_data(raw_tables)

        layout = layout_override
        if layout_path:
            try:
                xl = pd.ExcelFile(layout_path)
                layout = {}
                for sheet in ["Ids", "Historico", "Data"]:
                    if sheet in xl.sheet_names:
                        cols = list(xl.parse(sheet).columns)
                        if sheet == "Data":
                            cols = [
                                "Absorcion" if c == "Absorción L12M" else "Absorcion_H" if c == "Absorción Hist." else c
                                for c in cols
                            ]
                        layout[sheet] = cols
            except Exception:
                layout = None

        sheets = self.calculation.build_minimal(
            raw_clean,
            layout,
            start_quarter,
            display_start_quarter,
            filter_path=filter_path,
        )
        consolidated = ConsolidatedData(
            projects=[],
            historico=sheets.get("Historico", pd.DataFrame()),
            ids=sheets.get("Ids", pd.DataFrame()),
            data=sheets.get("Data", pd.DataFrame()),
        )

        return ConsolidationResult(
            output_path=None,
            projects_count=consolidated.total_projects,
            quarters_count=consolidated.total_quarters,
            sheets=sheets,
        )
