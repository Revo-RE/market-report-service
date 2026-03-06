from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from market_report.observability.logging import get_logger


class GoogleSheetsUpdater:
    """Update an existing Google Sheets workbook with DataFrames."""

    def __init__(self, spreadsheet_id: str):
        self._spreadsheet_id = spreadsheet_id
        self._client: gspread.Client | None = None
        self._logger = get_logger(self.__class__.__name__)

    @staticmethod
    def _extract_folder_id(url: str) -> str:
        if "/folders/" in url:
            parts = url.split("/folders/")
            if len(parts) > 1:
                return parts[1].split("/")[0].split("?")[0]
        raise ValueError(f"Invalid Google Drive folder URL: {url}")

    @classmethod
    def from_drive_folder(cls, folder_url: str, sheet_name: str) -> "GoogleSheetsUpdater":
        cred_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or "credentials.json"
        if not Path(cred_path).exists():
            raise FileNotFoundError("Missing Google credentials.json or GOOGLE_SERVICE_ACCOUNT_FILE.")
        creds = Credentials.from_service_account_file(
            cred_path,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        drive = build("drive", "v3", credentials=creds)
        folder_id = cls._extract_folder_id(folder_url)
        query = (
            f"'{folder_id}' in parents and trashed=false "
            "and mimeType='application/vnd.google-apps.spreadsheet' "
            f"and name='{sheet_name}'"
        )
        results = (
            drive.files()
            .list(
                q=query,
                fields="files(id, name)",
                pageSize=10,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="allDrives",
            )
            .execute()
        )
        files = results.get("files", [])
        if files:
            return cls(files[0]["id"])

        created = (
            drive.files()
            .create(
                body={
                    "name": sheet_name,
                    "mimeType": "application/vnd.google-apps.spreadsheet",
                    "parents": [folder_id],
                },
                fields="id",
                supportsAllDrives=True,
            )
            .execute()
        )
        return cls(created["id"])

    def _get_client(self) -> gspread.Client:
        if self._client:
            return self._client
        cred_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or "credentials.json"
        if not Path(cred_path).exists():
            raise FileNotFoundError("Missing Google credentials.json or GOOGLE_SERVICE_ACCOUNT_FILE.")
        creds = Credentials.from_service_account_file(
            cred_path,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        self._client = gspread.authorize(creds)
        return self._client

    @staticmethod
    def _df_to_values(df: pd.DataFrame) -> list[list[object]]:
        safe = df.where(pd.notna(df), "")
        return [safe.columns.tolist()] + safe.values.tolist()

    @staticmethod
    def _col_to_a1(col_idx: int) -> str:
        result = ""
        while col_idx > 0:
            col_idx, rem = divmod(col_idx - 1, 26)
            result = chr(65 + rem) + result
        return result

    def _format_numeric_column(self, ws: gspread.Worksheet, df: pd.DataFrame, column: str, pattern: str) -> None:
        if column not in df.columns:
            return
        col_idx = df.columns.get_loc(column) + 1
        col_letter = self._col_to_a1(col_idx)
        try:
            ws.format(
                f"{col_letter}2:{col_letter}",
                {"numberFormat": {"type": "NUMBER", "pattern": pattern}},
            )
        except Exception as exc:
            self._logger.warning("Failed formatting column %s in sheet %s: %s", column, ws.title, exc)

    def update_tabs(self, tabs: Dict[str, pd.DataFrame]) -> None:
        client = self._get_client()
        sheet = client.open_by_key(self._spreadsheet_id)
        for name, df in tabs.items():
            try:
                ws = sheet.worksheet(name)
            except gspread.exceptions.WorksheetNotFound:
                rows = max(100, len(df) + 5)
                cols = max(10, len(df.columns) + 2)
                ws = sheet.add_worksheet(title=name, rows=rows, cols=cols)
            values = self._df_to_values(df)
            ws.clear()
            ws.update(values, value_input_option="USER_ENTERED")
            if name == "Tipologias":
                self._format_numeric_column(ws, df, "Absorcion", "0.00")
            self._logger.info("Updated sheet %s (%s rows)", name, len(df))

        # Remove default empty sheet if it exists (Sheet1/Hoja 1).
        for ws in sheet.worksheets():
            if ws.title in {"Sheet1", "Hoja 1", "Hoja1"} and ws.title not in tabs:
                try:
                    values = ws.get_all_values()
                    if not values or all(not any(cell.strip() for cell in row) for row in values):
                        sheet.del_worksheet(ws)
                        self._logger.info("Removed empty default sheet %s", ws.title)
                except Exception as exc:
                    self._logger.warning("Failed removing sheet %s: %s", ws.title, exc)
