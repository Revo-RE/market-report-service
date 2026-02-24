from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

from market_report.domain.entities.project import Project


@dataclass
class ConsolidatedData:
    projects: List[Project]
    historico: pd.DataFrame = field(default_factory=pd.DataFrame)
    ids: pd.DataFrame = field(default_factory=pd.DataFrame)
    data: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def total_projects(self) -> int:
        return len(self.projects)

    @property
    def total_quarters(self) -> int:
        if self.historico.empty:
            return 0
        return self.historico["Trimestre"].nunique()
