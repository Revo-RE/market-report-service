from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TableConfig:
    name: str
    source_tab: str
    column_mappings: Dict[str, str]
    required_columns: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    derived_from: Optional[str] = None
    group_by: List[str] = field(default_factory=list)
    order_by: Optional[str] = None
    order_by_kind: Optional[str] = None
    retain_all_columns: bool = False
    key_columns: List[str] = field(default_factory=list)
    quarter_column: Optional[str] = None


@dataclass(frozen=True)
class ChartConfig:
    name: str
    table: str
    chart_type: str
    x: str
    y: str
    aggregate: str
    output: str


@dataclass(frozen=True)
class SlideConfig:
    title: str
    chart: str
    layout: str


@dataclass(frozen=True)
class PptConfig:
    template: str
    slides: List[SlideConfig]


@dataclass(frozen=True)
class GoogleSheetsConfig:
    spreadsheet_id: str
    tabs: List[str]
    local_csv_dir: Optional[str] = None


@dataclass(frozen=True)
class ExcelFolderConfig:
    path: str
    sheet_name: str = "Sheet1"
    pattern: str = "*.xlsx"
    table_key: str = "raw"


@dataclass(frozen=True)
class GoogleDriveFolderConfig:
    folder_url: str
    sheet_name: str = "Sheet1"
    table_key: str = "raw"
    subfolder_name: Optional[str] = None


@dataclass(frozen=True)
class ReferenceConfig:
    path: str
    sheet: str
    table: str


@dataclass(frozen=True)
class ComparisonTabConfig:
    tab: str
    table: str
    key_columns: List[str] = field(default_factory=list)
    filter_quarters: List[str] = field(default_factory=list)
    rtol: float = 1e-6
    atol: float = 1e-3
    column_tolerances: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass(frozen=True)
class ComparisonConfig:
    enabled: bool = True
    reference_path: str = ""
    export_dir: str = "artifacts"
    tabs: List[ComparisonTabConfig] = field(default_factory=list)
    auto_filter_quarters: bool = True
    drop_unnamed: bool = True


@dataclass(frozen=True)
class OutputConfig:
    local_dir: str = "outputs"
    drive_folder_url: Optional[str] = None
    filename: Optional[str] = None
    drive_convert: bool = False
    keep_local: bool = True


@dataclass(frozen=True)
class ProjectConfig:
    project_name: str
    google_sheets: Optional[GoogleSheetsConfig] = None
    excel_folder: Optional[ExcelFolderConfig] = None
    google_drive_folder: Optional[GoogleDriveFolderConfig] = None
    reference: Optional[ReferenceConfig] = None
    comparison: Optional[ComparisonConfig] = None
    output: Optional[OutputConfig] = None
    tables: List[TableConfig] = field(default_factory=list)
    charts: List[ChartConfig] = field(default_factory=list)
    ppt: PptConfig = field(default_factory=lambda: PptConfig(template="", slides=[]))
    raw: Dict[str, Any] = field(default_factory=dict)
