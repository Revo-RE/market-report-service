from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
from typing import Dict, Optional

import pandas as pd

from market_report.adapters.chart_renderers.matplotlib import MatplotlibChartRenderer
from market_report.adapters.data_sources.google_drive_folder import GoogleDriveFolderDataSource
from market_report.adapters.data_sources.google_sheets import GoogleSheetsDataSource
from market_report.adapters.data_sources.local_excel_folder import LocalExcelFolderDataSource
from market_report.adapters.excel_writer import ExcelWriter
from market_report.adapters.narrative_engines.rules_based import RulesBasedNarrativeEngine
from market_report.adapters.storage.google_drive_upload import GoogleDriveUploader
from market_report.adapters.storage.local_fs import LocalFileSystemStorage
from market_report.application.services.charts import ChartsService
from market_report.application.services.compare import ComparisonService
from market_report.application.services.metrics import MetricsService
from market_report.application.services.narrative import NarrativeService
from market_report.application.services.ppt import PptService
from market_report.application.services.quality import QualityService
from market_report.application.services.replication import ReplicationService
from market_report.application.services.transform import TransformService
from market_report.config.loader import load_project_config
from market_report.observability.logging import get_logger
from market_report.ports.chart import ChartRenderer
from market_report.ports.data_source import DataSource
from market_report.ports.narrative import NarrativeEngine
from market_report.ports.ppt import PptRenderer
from market_report.ports.storage import Storage
from market_report.adapters.ppt_renderers.pptx import PptxRenderer


@dataclass
class PipelineResult:
    run_id: str
    output_dir: Path
    ppt_path: Path
    chart_paths: Dict[str, Path]
    metrics: Dict[str, object]
    tables: Dict[str, pd.DataFrame]
    consolidated_workbook_path: Optional[Path] = None
    comparison_summary: Optional[Dict[str, object]] = None


class MarketReportPipeline:
    """Application pipeline orchestrating report generation."""

    def __init__(
        self,
        data_source: DataSource,
        storage: Storage,
        chart_renderer: ChartRenderer,
        ppt_renderer: PptRenderer,
        narrative_engine: NarrativeEngine,
    ):
        self._data_source = data_source
        self._storage = storage
        self._chart_service = ChartsService(chart_renderer)
        self._ppt_service = PptService(ppt_renderer)
        self._narrative_service = NarrativeService(narrative_engine)
        self._transform_service = TransformService()
        self._quality_service = QualityService()
        self._metrics_service = MetricsService()
        self._replication_service = ReplicationService()
        self._comparison_service = ComparisonService()
        self._excel_writer = ExcelWriter()
        self._logger = get_logger(self.__class__.__name__)

    def run(self, config_path: str, default_config_path: Optional[str] = None, run_id: Optional[str] = None) -> PipelineResult:
        config = load_project_config(config_path, default_config_path)
        run_id = run_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir = self._storage.prepare_run_dir(run_id)
        charts_dir = run_dir / "charts"

        self._logger.info("Loading data for project %s", config.project_name)
        raw_tables = self._data_source.load()

        self._logger.info("Normalizing tables")
        normalized = self._transform_service.normalize(raw_tables, config.tables)

        # Get raw_clean with all 46 columns for downstream processing
        raw_clean = normalized.get("raw_clean", pd.DataFrame())
        if raw_clean.empty:
            # Fallback: use raw table directly if raw_clean wasn't created
            raw_clean = raw_tables.get("raw", pd.DataFrame())

        # Determine display start quarter (lookback window is handled in output trimming)
        display_start_quarter = None
        quarter_column = None
        config_display_start = None
        if getattr(config, "raw", None):
            config_display_start = config.raw.get("display_start_quarter")
            if not config_display_start and isinstance(config.raw.get("raw"), dict):
                config_display_start = config.raw["raw"].get("display_start_quarter")
        if config_display_start:
            display_start_quarter = config_display_start
        elif not raw_clean.empty and "Último Trimestre" in raw_clean.columns:
            quarter_column = "Último Trimestre"
            display_start_quarter = self._transform_service.compute_display_start_quarter(
                raw_clean, quarter_column
            )
        else:
            for table_cfg in config.tables:
                if table_cfg.quarter_column and table_cfg.name in normalized:
                    candidate = normalized.get(table_cfg.name, pd.DataFrame())
                    if not candidate.empty and table_cfg.quarter_column in candidate.columns:
                        quarter_column = table_cfg.quarter_column
                        display_start_quarter = self._transform_service.compute_display_start_quarter(
                            candidate, quarter_column
                        )
                        break

        self._logger.info("Running QC checks")
        self._quality_service.validate(normalized, config.tables)

        # Generate all golden tabs
        self._logger.info("Generating all golden workbook tabs")
        all_tabs = self._replication_service.generate_all_tabs(normalized, raw_clean)

        # Optional: format Histórico_Mercado using golden header/order
        golden_hist_path = None
        golden_hist_sheet = None
        if getattr(config, "raw", None):
            raw_cfg = config.raw if isinstance(config.raw, dict) else {}
            golden_hist_path = raw_cfg.get("golden_hist_path")
            golden_hist_sheet = raw_cfg.get("golden_hist_sheet")
            if not golden_hist_path and isinstance(raw_cfg.get("raw"), dict):
                golden_hist_path = raw_cfg["raw"].get("golden_hist_path")
                golden_hist_sheet = raw_cfg["raw"].get("golden_hist_sheet")
        if "Histórico_Mercado" in all_tabs:
            # Apply Histórico_Mercado formulas and rounding before header alignment
            hist = all_tabs["Histórico_Mercado"].copy()
            price_col = "Precio Promedio Inv."
            m2_col = "M2 Promedio Inv"
            xm2_col = "$M2 Promedio Inv"
            if price_col in hist.columns and m2_col in hist.columns:
                price = pd.to_numeric(hist[price_col], errors="coerce")
                m2 = pd.to_numeric(hist[m2_col], errors="coerce")
                xm2 = price.divide(m2)
                hist[xm2_col] = xm2
            all_tabs["Histórico_Mercado"] = hist

        if golden_hist_path and golden_hist_sheet and "Histórico_Mercado" in all_tabs:
            try:
                golden_hist = pd.read_excel(golden_hist_path, sheet_name=golden_hist_sheet, header=None)
                header_row = golden_hist.iloc[0].tolist()
                data = all_tabs["Histórico_Mercado"].copy()
                # align columns to golden header order
                data_cols = [c for c in header_row if isinstance(c, str) and c in data.columns]
                data = data.reindex(columns=data_cols)
                # pad to golden width
                target_cols = len(header_row)
                rows = []
                rows.append(header_row)
                for _, row in data.iterrows():
                    row_vals = row.tolist()
                    if len(row_vals) < target_cols:
                        row_vals += [None] * (target_cols - len(row_vals))
                    rows.append(row_vals[:target_cols])
                all_tabs["Histórico_Mercado"] = pd.DataFrame(rows)
            except Exception as exc:
                self._logger.warning("Failed to format Histórico_Mercado using golden header: %s", exc)

        # Apply lookback window to output tables (keep full data for calculations)
        if display_start_quarter:
            trimmed_tabs: Dict[str, pd.DataFrame] = {}
            for tab_name, table in all_tabs.items():
                if table.empty:
                    trimmed_tabs[tab_name] = table
                    continue
                if quarter_column and quarter_column in table.columns:
                    trimmed_tabs[tab_name] = self._transform_service.apply_quarter_window(
                        table, quarter_column, display_start_quarter
                    )
                elif "Último Trimestre" in table.columns:
                    trimmed_tabs[tab_name] = self._transform_service.apply_quarter_window(
                        table, "Último Trimestre", display_start_quarter
                    )
                elif tab_name == "Insumos_HistóricosSanJosé" and 1 in table.columns:
                    start_key = self._transform_service._quarter_key(display_start_quarter)
                    def _keep_hist(value: object) -> bool:
                        if pd.isna(value):
                            return True
                        key = self._transform_service._quarter_key(str(value))
                        if key == (9999, 9):
                            return True
                        return key >= start_key

                    mask = table[1].apply(_keep_hist)
                    trimmed_tabs[tab_name] = table.loc[mask].copy()
                else:
                    trimmed_tabs[tab_name] = table
            all_tabs = trimmed_tabs

        # Export tabs to CSV for auditing
        pipeline_tabs_dir = run_dir / "pipeline_tabs"
        pipeline_tabs_dir.mkdir(exist_ok=True)
        self._excel_writer.export_tabs_to_csv(all_tabs, pipeline_tabs_dir)

        # Compare against golden if configured
        comparison_summary = None
        if config.comparison and config.comparison.enabled:
            self._logger.info("Comparing against golden reference")
            comparison_summary = self._comparison_service.compare_tabs(all_tabs, config.comparison)
            
            if comparison_summary["tabs_diff"]:
                self._logger.warning(
                    "Comparison found differences in tabs: %s", comparison_summary["tabs_diff"]
                )
            if comparison_summary["tabs_ok"]:
                self._logger.info(
                    "Comparison passed for tabs: %s", comparison_summary["tabs_ok"]
                )

        # Generate consolidated workbook
        consolidated_path = None
        if config.output:
            output_filename = config.output.filename or f"{config.project_name.replace(' ', '_').lower()}_consolidado.xlsx"
            consolidated_path = run_dir / output_filename
            
            # Get tab order from golden metadata if available
            tab_order = None
            metadata = getattr(self._replication_service, "_metadata", {})
            if metadata and "tabs" in metadata:
                tab_order = metadata["tabs"]
            
            self._logger.info("Generating consolidated workbook: %s", consolidated_path)
            self._excel_writer.write_workbook(all_tabs, consolidated_path, tab_order)
            
            # Upload to Google Drive if configured
            target_drive_folder = config.output.drive_folder_url
            if not target_drive_folder and hasattr(self._data_source, "resolved_folder_url"):
                target_drive_folder = getattr(self._data_source, "resolved_folder_url")

            if target_drive_folder:
                self._logger.info("Uploading to Google Drive: %s", target_drive_folder)
                uploader = GoogleDriveUploader()
                try:
                    file_id = uploader.upload_file(
                        consolidated_path,
                        target_drive_folder,
                        output_filename,
                        convert_to_sheets=bool(config.output and config.output.drive_convert),
                    )
                    self._logger.info("File uploaded to Google Drive. File ID: %s", file_id)
                    if config.output and config.output.drive_convert:
                        uploader.apply_sheet_formats(
                            file_id,
                            sheet_name="Histórico_Mercado",
                            column_formats={
                                "Precio Promedio Inv.": {"type": "CURRENCY", "pattern": "\"$\"#,##0"},
                                "$M2 Promedio Inv": {"type": "CURRENCY", "pattern": "\"$\"#,##0"},
                                "Absorción por Proyecto": {"type": "NUMBER", "pattern": "0.00"},
                                "Meses de Inventario": {"type": "NUMBER", "pattern": "0"},
                                "M2 Promedio Inv": {"type": "NUMBER", "pattern": "0"},
                                "Latitud": {"type": "NUMBER", "pattern": "0.0000"},
                                "Longitud": {"type": "NUMBER", "pattern": "0.0000"},
                            },
                            bold_header=True,
                        )
                    if config.output and not config.output.keep_local:
                        try:
                            shutil.rmtree(run_dir)
                            self._logger.info("Removed local output directory: %s", run_dir)
                        except Exception as exc:
                            self._logger.warning("Failed to remove local output directory %s: %s", run_dir, exc)
                except Exception as e:
                    self._logger.error("Failed to upload to Google Drive: %s", e)

        # Legacy comparison (if reference config exists but no comparison config)
        if config.reference and not config.comparison:
            self._logger.info("Comparing against reference sheet (legacy)")
            self._quality_service.compare_to_reference(
                normalized.get(config.reference.table, pd.DataFrame()),
                config.reference.path,
                config.reference.sheet,
            )

        self._logger.info("Computing metrics")
        metrics = self._metrics_service.compute(normalized)

        self._logger.info("Generating charts")
        chart_tables = normalized
        if display_start_quarter:
            chart_tables = {}
            for name, table in normalized.items():
                if table.empty:
                    chart_tables[name] = table
                    continue
                if quarter_column and quarter_column in table.columns:
                    chart_tables[name] = self._transform_service.apply_quarter_window(
                        table, quarter_column, display_start_quarter
                    )
                elif "Último Trimestre" in table.columns:
                    chart_tables[name] = self._transform_service.apply_quarter_window(
                        table, "Último Trimestre", display_start_quarter
                    )
                else:
                    chart_tables[name] = table
        chart_paths = self._chart_service.render(config.charts, chart_tables, charts_dir)

        self._logger.info("Generating narratives")
        narratives = self._narrative_service.generate(metrics)
        if narratives:
            (run_dir / "narratives.txt").write_text("\n".join(narratives.values()), encoding="utf-8")

        self._logger.info("Generating PPT deck")
        ppt_output_path = run_dir / f"{config.project_name.replace(' ', '_').lower()}_report.pptx"
        ppt_path = self._ppt_service.render(config.ppt, chart_paths, ppt_output_path)

        return PipelineResult(
            run_id=run_id,
            output_dir=run_dir,
            ppt_path=ppt_path,
            chart_paths=chart_paths,
            metrics=metrics,
            tables=normalized,
            consolidated_workbook_path=consolidated_path,
            comparison_summary=comparison_summary,
        )


def build_default_pipeline(config_path: str) -> MarketReportPipeline:
    config = load_project_config(config_path)
    if config.google_drive_folder:
        data_source = GoogleDriveFolderDataSource(config.google_drive_folder)
    elif config.excel_folder:
        data_source = LocalExcelFolderDataSource(config.excel_folder)
    elif config.google_sheets:
        data_source = GoogleSheetsDataSource(config.google_sheets)
    else:
        raise ValueError("No data source configured. Set google_drive_folder, excel_folder, or google_sheets in config.")
    return MarketReportPipeline(
        data_source=data_source,
        storage=LocalFileSystemStorage(),
        chart_renderer=MatplotlibChartRenderer(),
        ppt_renderer=PptxRenderer(),
        narrative_engine=RulesBasedNarrativeEngine(),
    )
