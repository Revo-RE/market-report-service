from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd


@dataclass
class ValidationResult:
    passed: bool
    avg_diff: float
    warnings: List[str]
    details: Dict[str, float]


class ValidationService:
    def __init__(self, tolerance_pct: float = 2.0):
        self.tolerance_pct = tolerance_pct

    def validate(self, sheets: Dict[str, pd.DataFrame], reference: Dict[str, pd.DataFrame]) -> ValidationResult:
        warnings: List[str] = []
        details: Dict[str, float] = {}

        # Placeholder: compare totals when available
        for key in ["Historico", "Data"]:
            if key in sheets and key in reference:
                diff = self._compare_totals(reference[key], sheets[key])
                details[f"{key}_diff"] = diff
                if diff > self.tolerance_pct:
                    warnings.append(f"{key} diff {diff:.2f}%")

        avg_diff = sum(details.values()) / len(details) if details else 0.0
        return ValidationResult(
            passed=not warnings,
            avg_diff=avg_diff,
            warnings=warnings,
            details=details,
        )

    def _compare_totals(self, ref: pd.DataFrame, ours: pd.DataFrame) -> float:
        if ref.empty or ours.empty:
            return 0.0
        ref_total = ref.select_dtypes(include=["number"]).sum(numeric_only=True).sum()
        our_total = ours.select_dtypes(include=["number"]).sum(numeric_only=True).sum()
        if ref_total == 0:
            return 0.0
        return abs((our_total - ref_total) / ref_total * 100)
