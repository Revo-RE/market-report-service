from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


class ComparisonService:
    """Compare pipeline tables against a reference workbook and emit diff reports."""

    def compare_single(
        self,
        table: pd.DataFrame,
        reference_path: str,
        sheet_name: str,
        key_columns: List[str],
        filter_quarters: List[str],
        rtol: float,
        atol: float,
        column_tolerances: Dict[str, Dict[str, float]],
        report_path: str | None = None,
    ) -> Dict[str, object]:
        if table.empty:
            return self._write_report(
                {
                    "status": "missing_table",
                    "tab": sheet_name,
                    "issues": ["pipeline table is empty"],
                },
                report_path,
            )

        reference = pd.read_excel(reference_path, sheet_name=sheet_name)
        reference = reference.loc[:, ~reference.columns.astype(str).str.startswith("Unnamed")].copy()
        if filter_quarters and "Último Trimestre" in reference.columns and "Último Trimestre" in table.columns:
            reference = reference[reference["Último Trimestre"].isin(filter_quarters)]
            table = table[table["Último Trimestre"].isin(filter_quarters)]

        missing_columns = sorted(set(reference.columns) - set(table.columns))
        extra_columns = sorted(set(table.columns) - set(reference.columns))

        # Align columns to reference order for consistent comparison
        table_aligned = table.copy()
        if missing_columns:
            # Keep for reporting but comparison will likely fail
            pass
        else:
            table_aligned = table_aligned[reference.columns]

        result: Dict[str, object] = {
            "status": "ok",
            "tab": sheet_name,
            "row_counts": {
                "pipeline": int(len(table_aligned)),
                "reference": int(len(reference)),
            },
            "column_diff": {
                "missing": missing_columns,
                "extra": extra_columns,
            },
            "missing_keys": [],
            "extra_keys": [],
            "value_mismatches": {},
            "samples": {},
        }

        if missing_columns or extra_columns:
            result["status"] = "diff"

        # If no key columns specified, fall back to full row compare
        if key_columns and all(col in reference.columns for col in key_columns):
            ref_index = reference.set_index(key_columns)
            tbl_index = table_aligned.set_index(key_columns)
            if ref_index.index.has_duplicates or tbl_index.index.has_duplicates:
                result["status"] = "diff"
                result["issues"] = ["duplicate keys detected"]

            ref_keys = set(ref_index.index)
            tbl_keys = set(tbl_index.index)
            result["missing_keys"] = [self._key_to_dict(k, key_columns) for k in sorted(ref_keys - tbl_keys)]
            result["extra_keys"] = [self._key_to_dict(k, key_columns) for k in sorted(tbl_keys - ref_keys)]

            common_keys = sorted(ref_keys & tbl_keys)
            ref_common = ref_index.loc[common_keys]
            tbl_common = tbl_index.loc[common_keys]

            self._compare_values(
                reference=ref_common,
                table=tbl_common,
                result=result,
                rtol=rtol,
                atol=atol,
                column_tolerances=column_tolerances,
            )
        else:
            # Fallback: compare sorted rows when keys are not provided
            ref_sorted = reference.sort_values(by=reference.columns.tolist()).reset_index(drop=True)
            tbl_sorted = table_aligned.sort_values(by=table_aligned.columns.tolist()).reset_index(drop=True)
            if len(ref_sorted) != len(tbl_sorted):
                result["status"] = "diff"
            self._compare_values(
                reference=ref_sorted,
                table=tbl_sorted,
                result=result,
                rtol=rtol,
                atol=atol,
                column_tolerances=column_tolerances,
            )

        if result["missing_keys"] or result["extra_keys"] or result["value_mismatches"]:
            result["status"] = "diff"

        return self._write_report(result, report_path)

    def compare_tabs(self, tables: Dict[str, pd.DataFrame], config) -> Dict[str, object]:
        summary = {"tabs_ok": [], "tabs_diff": [], "tabs_missing": [], "details": {}}
        for tab_cfg in config.tabs:
            # Try to get table by the configured name, or by tab name as fallback
            table = tables.get(tab_cfg.table, tables.get(tab_cfg.tab, pd.DataFrame()))
            report_path = None
            if config.export_dir:
                report_dir = Path(config.export_dir) / "diff_reports"
                report_dir.mkdir(parents=True, exist_ok=True)
                report_path = str(report_dir / f"{tab_cfg.tab}_diff.json")

            result = self.compare_single(
                table=table,
                reference_path=config.reference_path,
                sheet_name=tab_cfg.tab,
                key_columns=tab_cfg.key_columns,
                filter_quarters=tab_cfg.filter_quarters,
                rtol=tab_cfg.rtol,
                atol=tab_cfg.atol,
                column_tolerances=tab_cfg.column_tolerances,
                report_path=report_path,
            )
            summary["details"][tab_cfg.tab] = result
            if result["status"] == "ok":
                summary["tabs_ok"].append(tab_cfg.tab)
            elif result["status"] == "missing_table":
                summary["tabs_missing"].append(tab_cfg.tab)
            else:
                summary["tabs_diff"].append(tab_cfg.tab)
        return summary

    def _compare_values(
        self,
        reference: pd.DataFrame,
        table: pd.DataFrame,
        result: Dict[str, object],
        rtol: float,
        atol: float,
        column_tolerances: Dict[str, Dict[str, float]],
    ) -> None:
        for col in reference.columns:
            ref_col = reference[col]
            tbl_col = table[col]
            ref_num = pd.to_numeric(ref_col, errors="coerce")
            tbl_num = pd.to_numeric(tbl_col, errors="coerce")
            num_ratio = min(ref_num.notna().mean(), tbl_num.notna().mean())
            if num_ratio > 0.8:
                tol = column_tolerances.get(col, {})
                col_rtol = tol.get("rtol", rtol)
                col_atol = tol.get("atol", atol)
                matches = np.isclose(ref_num, tbl_num, rtol=col_rtol, atol=col_atol, equal_nan=True)
                mismatch_count = int((~matches).sum())
                if mismatch_count > 0:
                    result["value_mismatches"][col] = mismatch_count
                    result["samples"].setdefault(col, [])
                    mismatch_idx = np.where(~matches)[0][:5]
                    for idx in mismatch_idx:
                        result["samples"][col].append(
                            {
                                "index": int(idx),
                                "reference": self._normalize_value(ref_col.iloc[idx]),
                                "pipeline": self._normalize_value(tbl_col.iloc[idx]),
                            }
                        )
            else:
                ref_str = ref_col.map(self._normalize_value)
                tbl_str = tbl_col.map(self._normalize_value)
                mismatch = ref_str != tbl_str
                mismatch_count = int(mismatch.sum())
                if mismatch_count > 0:
                    result["value_mismatches"][col] = mismatch_count
                    result["samples"].setdefault(col, [])
                    mismatch_idx = mismatch[mismatch].index[:5]
                    for idx in mismatch_idx:
                        result["samples"][col].append(
                            {
                                "index": str(idx),  # Keep as string to handle non-numeric indices
                                "reference": ref_str.loc[idx],
                                "pipeline": tbl_str.loc[idx],
                            }
                        )

    @staticmethod
    def _normalize_value(value: object) -> str:
        if pd.isna(value):
            return ""
        text = str(value).strip()
        if text.endswith(".0"):
            text = text[:-2]
        return text

    @staticmethod
    def _key_to_dict(key, key_columns: List[str]) -> Dict[str, object]:
        if not isinstance(key, tuple):
            return {key_columns[0]: key}
        return dict(zip(key_columns, key))

    @staticmethod
    def _write_report(result: Dict[str, object], report_path: str | None) -> Dict[str, object]:
        if report_path:
            Path(report_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
