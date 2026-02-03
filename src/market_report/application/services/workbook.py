from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd


class WorkbookBuilder:
    """Build an Excel workbook from a set of tables."""

    def __init__(self, tab_order: List[str] | None = None):
        self._tab_order = tab_order or []

    def build(self, tables: Dict[str, pd.DataFrame], output_path: Path, tab_order: List[str] | None = None) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        order = tab_order or self._tab_order or list(tables.keys())

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for tab in order:
                df = tables.get(tab, pd.DataFrame())
                if len(tab) > 31:
                    raise ValueError(f"Sheet name exceeds Excel limit (31): {tab}")
                df.to_excel(writer, index=False, sheet_name=tab)
        return output_path
