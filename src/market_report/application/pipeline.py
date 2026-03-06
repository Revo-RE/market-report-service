from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
from typing import Dict, Optional
import tempfile

import json
import hashlib
import os
import pandas as pd

from market_report.adapters.chart_renderers.matplotlib import MatplotlibChartRenderer
from market_report.adapters.data_sources.google_drive_folder import GoogleDriveFolderDataSource
from market_report.adapters.data_sources.google_sheets import GoogleSheetsDataSource
from market_report.adapters.data_sources.local_excel_folder import LocalExcelFolderDataSource
from market_report.adapters.excel_writer import ExcelWriter
from market_report.adapters.narrative_engines.rules_based import RulesBasedNarrativeEngine
from market_report.adapters.storage.google_drive_upload import GoogleDriveUploader
from market_report.adapters.storage.google_sheets_update import GoogleSheetsUpdater
from market_report.adapters.storage.google_drive_audit import GoogleDriveAuditStore
from market_report.adapters.storage.local_fs import LocalFileSystemStorage
from market_report.application.services.charts import ChartsService
from market_report.application.services.metrics import MetricsService
from market_report.application.services.narrative import NarrativeService
from market_report.application.services.ppt import PptService
from market_report.application.services.quality import QualityService
from typing import Any
from market_report.application.orchestrator import ConsolidationOrchestrator
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
    layers: Optional[Any] = None
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
        self._excel_writer = ExcelWriter()
        self._logger = get_logger(self.__class__.__name__)

    def run(self, config_path: str, default_config_path: Optional[str] = None, run_id: Optional[str] = None) -> PipelineResult:
        config = load_project_config(config_path, default_config_path)
        run_id = run_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if (
            getattr(config, "output", None)
            and config.output
            and getattr(config.output, "keep_local", True) is False
        ):
            run_dir = Path(tempfile.mkdtemp(prefix="market_report_run_"))
        else:
            run_dir = self._storage.prepare_run_dir(run_id)
        charts_dir = run_dir / "charts"
        skip_local = bool(os.getenv("SKIP_LOCAL_OUTPUTS"))

        # Minimal 3-sheet consolidated output (layout-driven)
        minimal_cfg = {}
        if getattr(config, "raw", None):
            minimal_root = config.raw if isinstance(config.raw, dict) else {}
            # support config.raw being the full config, with nested "raw" settings
            minimal_cfg = minimal_root.get("raw", minimal_root)
        if minimal_cfg.get("minimal_output"):
            source_path = minimal_cfg.get("minimal_source_path")
            layout_path = minimal_cfg.get("minimal_layout_path")
            layout_override = minimal_cfg.get("minimal_layout")
            start_quarter = minimal_cfg.get("minimal_start_quarter")
            display_start = minimal_cfg.get("minimal_display_start_quarter")
            filter_path = minimal_cfg.get("minimal_filter_path")
            if not source_path:
                raise ValueError("minimal_source_path is required when minimal_output is enabled")

            self._logger.info("Building minimal consolidated workbook from %s", source_path)
            self._logger.info("Loading data for project %s", config.project_name)
            raw_tables = self._data_source.load()

            self._logger.info("Normalizing tables")
            normalized = self._transform_service.normalize(raw_tables, config.tables)

            raw_clean = normalized.get("raw_clean", pd.DataFrame())
            if raw_clean.empty:
                raw_clean = raw_tables.get("raw", pd.DataFrame())

            orchestrator = ConsolidationOrchestrator()
            result = orchestrator.execute(
                raw_tables={"raw": raw_clean},
                layout_path=layout_path,
                layout_override=layout_override,
                start_quarter=start_quarter,
                display_start_quarter=display_start,
                filter_path=filter_path,
            )
            minimal_tabs = result.sheets

            def _hash_df(df: pd.DataFrame) -> str:
                if df.empty:
                    return ""
                safe = df.copy()
                safe = safe.where(pd.notna(safe), "")
                data = safe.to_csv(index=False).encode("utf-8")
                return hashlib.sha256(data).hexdigest()

            def _audit_payload() -> Dict[str, object]:
                return {
                    "city": config.project_name,
                    "run_id": run_id,
                    "timestamp_utc": datetime.utcnow().isoformat() + "Z",
                    "source_folder": getattr(config.google_drive_folder, "folder_url", None),
                    "rows": {k: int(v.shape[0]) for k, v in minimal_tabs.items()},
                    "cols": {k: int(v.shape[1]) for k, v in minimal_tabs.items()},
                    "hash": {k: _hash_df(v) for k, v in minimal_tabs.items()},
                }

            def _diff_summary(prev: Dict[str, object], curr: Dict[str, object]) -> Dict[str, object]:
                summary: Dict[str, object] = {"changed": False, "by_sheet": {}}
                prev_hash = prev.get("hash", {}) if prev else {}
                prev_rows = prev.get("rows", {}) if prev else {}
                prev_cols = prev.get("cols", {}) if prev else {}
                for sheet_name in minimal_tabs.keys():
                    curr_hash = curr.get("hash", {}).get(sheet_name)
                    summary["by_sheet"][sheet_name] = {
                        "hash_changed": curr_hash != prev_hash.get(sheet_name),
                        "rows_prev": prev_rows.get(sheet_name),
                        "rows_curr": curr.get("rows", {}).get(sheet_name),
                        "cols_prev": prev_cols.get(sheet_name),
                        "cols_curr": curr.get("cols", {}).get(sheet_name),
                    }
                summary["changed"] = any(v["hash_changed"] for v in summary["by_sheet"].values())
                return summary

            if config.output and config.output.drive_folder_url:
                try:
                    sheet_name = f"{config.project_name}_Consolidado"
                    self._logger.info("Updating charts sheet %s", sheet_name)
                    updater = GoogleSheetsUpdater.from_drive_folder(
                        config.output.drive_folder_url,
                        sheet_name,
                    )
                    updater.update_tabs(
                        {
                            "Ids": minimal_tabs.get("Ids", pd.DataFrame()),
                            "Historico": minimal_tabs.get("Historico", pd.DataFrame()),
                            "Data": minimal_tabs.get("Data", pd.DataFrame()),
                            "Tipologias": minimal_tabs.get("Tipologias", pd.DataFrame()),
                        }
                    )
                except Exception as exc:
                    self._logger.warning("Charts sheet update skipped: %s", exc)

            audit_folder = minimal_cfg.get("audit_drive_folder_url")
            if audit_folder:
                try:
                    audit_store = GoogleDriveAuditStore(audit_folder)
                    current_audit = _audit_payload()
                    latest_name = f"{config.project_name}_audit_latest.json"
                    prev_audit = audit_store.download_json(latest_name)
                    diff = _diff_summary(prev_audit or {}, current_audit)
                    audit_store.upload_json(latest_name, current_audit)
                    audit_store.upload_json(
                        f"{config.project_name}_audit_{run_id}.json",
                        current_audit,
                    )
                    audit_store.upload_json(
                        f"{config.project_name}_audit_diff_{run_id}.json",
                        diff,
                    )
                except Exception as exc:
                    self._logger.warning("Audit logging skipped: %s", exc)

            consolidated_path = None
            if config.output and not skip_local:
                output_filename = config.output.filename or "consolidado.xlsx"
                consolidated_path = run_dir / output_filename
                self._excel_writer.write_workbook(
                    minimal_tabs,
                    consolidated_path,
                    tab_order=["Ids", "Historico", "Data", "Tipologias"],
                )

                target_drive_folder = config.output.drive_folder_url
                skip_upload = bool(os.getenv("SKIP_DRIVE_UPLOAD")) or getattr(config.output, "skip_drive_upload", False)
                if skip_local:
                    skip_upload = True
                if target_drive_folder and not skip_upload:
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
                            try:
                                if consolidated_path.exists():
                                    consolidated_path.unlink()
                                    self._logger.info("Removed local Excel after conversion: %s", consolidated_path)
                            except Exception as exc:
                                self._logger.warning("Failed removing local Excel %s: %s", consolidated_path, exc)
                        if config.output and not config.output.keep_local:
                            try:
                                shutil.rmtree(run_dir)
                                self._logger.info("Removed local output directory: %s", run_dir)
                            except Exception as exc:
                                self._logger.warning("Failed to remove local output directory %s: %s", run_dir, exc)
                    except Exception as e:
                        self._logger.error("Failed to upload to Google Drive: %s", e)
            if skip_local:
                try:
                    shutil.rmtree(run_dir, ignore_errors=True)
                except Exception:
                    pass

            return PipelineResult(
                run_id=run_id,
                output_dir=run_dir,
                ppt_path=Path(),
                chart_paths={},
                metrics={},
                tables={},
                layers=None,
                consolidated_workbook_path=consolidated_path,
                comparison_summary=None,
            )

        raise RuntimeError("Legacy pipeline disabled. Enable minimal_output to run MVP.")


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
