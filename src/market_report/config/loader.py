from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from market_report.config.schemas import (
    ChartConfig,
    ComparisonConfig,
    ComparisonTabConfig,
    ExcelFolderConfig,
    GoogleDriveFolderConfig,
    GoogleSheetsConfig,
    OutputConfig,
    PptConfig,
    ProjectConfig,
    ReferenceConfig,
    SlideConfig,
    TableConfig,
)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_project_config(project_path: str, default_path: str | None = None) -> ProjectConfig:
    project_data = _load_json(Path(project_path))
    if default_path:
        default_data = _load_json(Path(default_path))
        data = _deep_merge(default_data, project_data)
    else:
        data = project_data

    gs = data.get("google_sheets")
    excel_folder = data.get("excel_folder")
    google_drive_folder = data.get("google_drive_folder")
    reference = data.get("reference")
    comparison = data.get("comparison")
    output = data.get("output")
    tables = [
        TableConfig(
            name=table["name"],
            source_tab=table["source_tab"],
            column_mappings=table.get("column_mappings", {}),
            required_columns=table.get("required_columns", []),
            required_fields=table.get("required_fields", []),
            derived_from=table.get("derived_from"),
            group_by=table.get("group_by", []),
            order_by=table.get("order_by"),
            order_by_kind=table.get("order_by_kind"),
            retain_all_columns=table.get("retain_all_columns", False),
            key_columns=table.get("key_columns", []),
            quarter_column=table.get("quarter_column"),
        )
        for table in data.get("tables", [])
    ]
    charts = [
        ChartConfig(
            name=chart["name"],
            table=chart["table"],
            chart_type=chart.get("type", "bar"),
            x=chart["x"],
            y=chart["y"],
            aggregate=chart.get("aggregate", "sum"),
            output=chart.get("output", f"{chart['name']}.png"),
        )
        for chart in data.get("charts", [])
    ]
    ppt_slides = [
        SlideConfig(
            title=slide["title"],
            chart=slide["chart"],
            layout=slide.get("layout", "title_and_chart"),
        )
        for slide in data.get("ppt", {}).get("slides", [])
    ]
    ppt = PptConfig(
        template=data.get("ppt", {}).get("template", "templates/mvp_template.pptx"),
        slides=ppt_slides,
    )

    return ProjectConfig(
        project_name=data.get("project_name", "Unknown"),
        google_sheets=GoogleSheetsConfig(
            spreadsheet_id=gs.get("spreadsheet_id", ""),
            tabs=gs.get("tabs", []),
            local_csv_dir=gs.get("local_csv_dir"),
        )
        if gs
        else None,
        excel_folder=ExcelFolderConfig(
            path=excel_folder["path"],
            sheet_name=excel_folder.get("sheet_name", "Sheet1"),
            pattern=excel_folder.get("pattern", "*.xlsx"),
            table_key=excel_folder.get("table_key", "raw"),
        )
        if excel_folder
        else None,
        google_drive_folder=GoogleDriveFolderConfig(
            folder_url=google_drive_folder["folder_url"],
            sheet_name=google_drive_folder.get("sheet_name", "Sheet1"),
            table_key=google_drive_folder.get("table_key", "raw"),
            subfolder_name=google_drive_folder.get("subfolder_name"),
        )
        if google_drive_folder
        else None,
        reference=ReferenceConfig(
            path=reference["path"],
            sheet=reference["sheet"],
            table=reference["table"],
        )
        if reference
        else None,
        comparison=ComparisonConfig(
            enabled=comparison.get("enabled", True),
            reference_path=comparison.get("reference_path", reference["path"] if reference else ""),
            export_dir=comparison.get("export_dir", "artifacts"),
            tabs=[
                ComparisonTabConfig(
                    tab=item["tab"],
                    table=item["table"],
                    key_columns=item.get("key_columns", []),
                    filter_quarters=item.get("filter_quarters", []),
                    rtol=item.get("rtol", 1e-6),
                    atol=item.get("atol", 1e-3),
                    column_tolerances=item.get("column_tolerances", {}),
                )
                for item in comparison.get("tabs", [])
            ],
            auto_filter_quarters=comparison.get("auto_filter_quarters", True),
            drop_unnamed=comparison.get("drop_unnamed", True),
        )
        if comparison
        else None,
        output=OutputConfig(
            local_dir=output.get("local_dir", "outputs"),
            drive_folder_url=output.get("drive_folder_url"),
            filename=output.get("filename"),
            drive_convert=output.get("drive_convert", False),
            keep_local=output.get("keep_local", True),
        )
        if output
        else None,
        tables=tables,
        charts=charts,
        ppt=ppt,
        raw=data,
    )
