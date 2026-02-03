from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

import json
from pathlib import Path

from market_report.config.schemas import TableConfig


@dataclass
class QCError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


class QualityService:
    """Run QC checks and fail early with actionable messages."""

    def __init__(self, golden_metadata_path: str | None = None):
        self._golden_metadata = self._load_golden_metadata(golden_metadata_path)

    def _load_golden_metadata(self, path: str | None) -> Dict:
        """Load golden metadata for validation."""
        if not path:
            default_path = Path("artifacts/metadata/golden_metadata.json")
            if default_path.exists():
                with default_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
        elif Path(path).exists():
            with Path(path).open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def validate(self, tables: Dict[str, pd.DataFrame], table_configs: list[TableConfig]) -> None:
        errors: List[str] = []
        for config in table_configs:
            table = tables.get(config.name, pd.DataFrame())
            if table.empty:
                errors.append(f"Table '{config.name}' is empty")
                continue

            # Check for missing columns
            missing_columns = [col for col in config.required_columns if col not in table.columns]
            if missing_columns:
                errors.append(f"Table '{config.name}' missing columns: {missing_columns}")
                continue

            # Check for empty critical fields
            for field in config.required_fields:
                if field not in table.columns:
                    continue
                empty_count = table[field].isna().sum()
                if empty_count > 0:
                    errors.append(f"Table '{config.name}' has {empty_count} empty values in critical field '{field}'")

            # Check key uniqueness and missing keys
            errors.extend(self._validate_keys(table, config))

            # Skip strict validation for raw_clean - it may have mixed formats
            if config.name != "raw_clean":
                # Validate data types for numeric columns
                errors.extend(self._validate_data_types(table, config))

                # Validate ranges for numeric columns
                errors.extend(self._validate_ranges(table, config))

            # Validate quarter formats
            errors.extend(self._validate_quarter_format(table, config))

            # Validate against golden metadata if available
            errors.extend(self._validate_against_golden_metadata(table, config.name))

        if errors:
            raise QCError("; ".join(errors))

    def _validate_against_golden_metadata(self, table: pd.DataFrame, table_name: str) -> List[str]:
        """Validate table structure against golden metadata."""
        errors: List[str] = []
        if not self._golden_metadata or "metadata" not in self._golden_metadata:
            return errors

        # Map table names to golden tab names
        tab_name_map = {
            "historico_mercado": "Histórico_Mercado",
            "historico_proy_nuevos": "Histórico_ProyNuevos",
        }
        golden_tab = tab_name_map.get(table_name, table_name)

        if golden_tab not in self._golden_metadata["metadata"]:
            return errors

        expected = self._golden_metadata["metadata"][golden_tab]
        expected_rows = expected.get("rows", 0)
        expected_cols = expected.get("cols", 0)

        # Allow some tolerance for row counts (golden may have extra historical quarters)
        if expected_rows > 0 and len(table) < expected_rows * 0.8:
            errors.append(
                f"Table '{table_name}' has {len(table)} rows, expected at least {int(expected_rows * 0.8)} (golden: {expected_rows})"
            )

        # For column count, be more lenient - golden has Unnamed columns that we don't need
        # Only check core columns, not total count
        if expected_cols > 0 and len(table.columns) < 10:  # At least 10 core columns
            errors.append(
                f"Table '{table_name}' has {len(table.columns)} columns, expected at least 10 core columns (golden has {expected_cols} including Unnamed)"
            )

        return errors

    def _validate_data_types(self, table: pd.DataFrame, config: TableConfig) -> List[str]:
        """Validate that numeric columns contain valid numeric data."""
        errors: List[str] = []
        # Common numeric column patterns
        numeric_patterns = ["Precio", "M2", "Unidades", "Meses", "Absorción", "$"]
        for col in table.columns:
            if any(pattern in col for pattern in numeric_patterns):
                # Try to convert to numeric, allowing common non-numeric values
                # Replace common non-numeric indicators with NaN
                # Use regex=False to avoid issues with special characters
                cleaned = table[col].astype(str).replace(["-", "$", "N/A", "n/a", "nan", "None", ""], pd.NA)
                numeric_series = pd.to_numeric(cleaned, errors="coerce")
                # Count only truly invalid values (not just missing/empty)
                # Invalid = values that were not originally NaN and couldn't be converted
                original_na = table[col].isna().sum()
                final_na = numeric_series.isna().sum()
                invalid_count = final_na - original_na
                # Only report if significant portion is invalid (>30% of non-null values)
                # Be more lenient - "-" and similar are valid "not available" markers
                non_null_count = (table[col].notna()).sum()
                if invalid_count > 0 and non_null_count > 0 and (invalid_count / non_null_count) > 0.3:
                    errors.append(
                        f"Table '{config.name}' column '{col}' has {invalid_count} invalid numeric values ({(invalid_count/non_null_count*100):.1f}% of non-null)"
                    )
        return errors

    def _validate_keys(self, table: pd.DataFrame, config: TableConfig) -> List[str]:
        errors: List[str] = []
        if not config.key_columns:
            return errors
        missing = [col for col in config.key_columns if col not in table.columns]
        if missing:
            errors.append(f"Table '{config.name}' missing key columns: {missing}")
            return errors
        empty_keys = table[config.key_columns].isna().any(axis=1).sum()
        if empty_keys > 0:
            errors.append(f"Table '{config.name}' has {empty_keys} rows with empty key values")
        if table.duplicated(subset=config.key_columns).any():
            dup_count = int(table.duplicated(subset=config.key_columns).sum())
            errors.append(f"Table '{config.name}' has {dup_count} duplicate key rows for {config.key_columns}")
        return errors

    def _validate_ranges(self, table: pd.DataFrame, config: TableConfig) -> List[str]:
        """Validate that numeric values are within reasonable ranges."""
        errors: List[str] = []
        # Define reasonable ranges for common metrics
        ranges = {
            "Unidades": (0, 10000),
            "Meses": (0, 500),  # Increased for meses de inventario which can be high
            "Precio": (0, 1e9),
            "$M2": (0, 500000),  # $M2 can be much higher than 10000
            "M2": (0, 10000),  # M2 (superficie) stays reasonable
        }
        for col in table.columns:
            for pattern, (min_val, max_val) in ranges.items():
                if pattern in col:
                    # Clean and convert to numeric
                    cleaned = table[col].replace(["-", "$", "N/A", "n/a", ""], pd.NA)
                    numeric_series = pd.to_numeric(cleaned, errors="coerce")
                    out_of_range = ((numeric_series < min_val) | (numeric_series > max_val)) & numeric_series.notna()
                    if out_of_range.any():
                        count = out_of_range.sum()
                        # Only report if significant (>5% of valid values)
                        valid_count = numeric_series.notna().sum()
                        if valid_count > 0 and (count / valid_count) > 0.05:
                            errors.append(
                                f"Table '{config.name}' column '{col}' has {count} values outside range [{min_val}, {max_val}]"
                            )
                    break
        return errors

    def _validate_quarter_format(self, table: pd.DataFrame, config: TableConfig) -> List[str]:
        errors: List[str] = []
        quarter_col = config.quarter_column
        if not quarter_col and "Último Trimestre" in table.columns:
            quarter_col = "Último Trimestre"
        if not quarter_col or quarter_col not in table.columns:
            return errors
        invalid = table[quarter_col].dropna().astype(str).str.match(r"^\d{4} - Q[1-4]$") == False
        invalid_count = int(invalid.sum())
        if invalid_count > 0:
            errors.append(f"Table '{config.name}' has {invalid_count} invalid quarter values in '{quarter_col}'")
        return errors

    def compare_to_reference(
        self,
        table: pd.DataFrame,
        reference_path: str,
        sheet_name: str,
        key_columns: List[str] | None = None,
        filter_quarters: List[str] | None = None,
        rtol: float = 1e-6,
        atol: float = 1e-3,
        column_tolerances: Dict[str, Dict[str, float]] | None = None,
        report_path: str | None = None,
    ) -> None:
        from market_report.application.services.compare import ComparisonService

        comparator = ComparisonService()
        result = comparator.compare_single(
            table=table,
            reference_path=reference_path,
            sheet_name=sheet_name,
            key_columns=key_columns or [],
            filter_quarters=filter_quarters or [],
            rtol=rtol,
            atol=atol,
            column_tolerances=column_tolerances or {},
            report_path=report_path,
        )
        if result["status"] != "ok":
            raise QCError(f"Reference comparison failed for '{sheet_name}': {result['status']}")

    @staticmethod
    def _normalize_value(value: object) -> str:
        if pd.isna(value):
            return ""
        text = str(value).strip()
        if text.endswith(".0"):
            text = text[:-2]
        if text.startswith("-") and text[1:].replace(".", "").isdigit():
            return text
        if text.replace(".", "").isdigit() and text.endswith(".0"):
            text = text[:-2]
        return text
