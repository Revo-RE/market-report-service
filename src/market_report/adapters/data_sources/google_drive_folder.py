from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Dict, List

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from market_report.config.schemas import GoogleDriveFolderConfig
from market_report.observability.logging import get_logger
from market_report.ports.data_source import DataSource


class GoogleDriveFolderDataSource(DataSource):
    """Load and concatenate multiple Google Sheets from a Google Drive folder."""

    def __init__(self, config: GoogleDriveFolderConfig):
        self._config = config
        self._client: gspread.Client | None = None
        self._logger = get_logger(self.__class__.__name__)
        self._resolved_folder_id: str | None = None
        self._resolved_folder_url: str | None = None

    @property
    def resolved_folder_url(self) -> str | None:
        return self._resolved_folder_url

    def _get_client(self) -> tuple[gspread.Client, Credentials]:
        """Get authenticated Google Sheets client and credentials."""
        if self._client is not None:
            # Get credentials from client
            creds = self._client.auth
            return self._client, creds

        # Try service account credentials first
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        if service_account_file and Path(service_account_file).exists():
            creds = Credentials.from_service_account_file(
                service_account_file,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets.readonly",
                    "https://www.googleapis.com/auth/drive.readonly",
                ],
            )
            self._client = gspread.authorize(creds)
            return self._client, creds

        # Fallback to OAuth2
        try:
            self._client = gspread.service_account()
            creds = self._client.auth
            return self._client, creds
        except Exception:
            raise RuntimeError(
                "Google Sheets authentication failed. Set GOOGLE_SERVICE_ACCOUNT_FILE env var "
                "or configure OAuth2 credentials. See: https://gspread.readthedocs.io/en/latest/oauth2.html"
            )

    def load(self) -> Dict[str, pd.DataFrame]:
        """Load and concatenate all sheets from the Google Drive folder."""
        client, creds = self._get_client()
        drive_service = build("drive", "v3", credentials=creds)

        # Get all files in the folder
        folder_id = self._extract_folder_id(self._config.folder_url)
        if self._config.subfolder_name:
            folder_id = self._find_subfolder_id(drive_service, folder_id, self._config.subfolder_name)
            self._resolved_folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        else:
            self._resolved_folder_url = self._config.folder_url
        self._resolved_folder_id = folder_id
        files = self._list_files_in_folder(drive_service, folder_id)

        if not files:
            raise FileNotFoundError(f"No Excel/Sheets files found in folder: {self._config.folder_url}")
        if len(files) > 20:
            raise RuntimeError(
                f"Too many files in Google Drive folder ({len(files)}). Expected 20 or fewer."
            )

        self._logger.info("Found %d files in Google Drive folder", len(files))
        
        frames: List[pd.DataFrame] = []
        for file_info in files:
            self._logger.debug("Processing file: %s (ID: %s)", file_info.get('name', 'Unknown'), file_info['id'])
            try:
                file_id = file_info["id"]
                mime_type = file_info.get("mimeType", "")
                
                # If it's a Google Sheet, use gspread
                if mime_type == "application/vnd.google-apps.spreadsheet":
                    spreadsheet = client.open_by_key(file_id)
                    worksheet = None
                    if self._config.sheet_name:
                        try:
                            worksheet = spreadsheet.worksheet(self._config.sheet_name)
                        except Exception:
                            self._logger.warning(
                                "Worksheet '%s' not found in %s. Falling back to first sheet.",
                                self._config.sheet_name,
                                file_info.get("name", file_id),
                            )
                    if worksheet is None:
                        worksheet = spreadsheet.get_worksheet(0)
                    records = worksheet.get_all_records()
                    if records:
                        df = pd.DataFrame(records)
                        frames.append(df)
                # If it's an Excel file, download and read it
                elif mime_type in [
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.ms-excel",
                ]:
                    # Download the file
                    request = drive_service.files().get_media(fileId=file_id)
                    file_content = io.BytesIO(request.execute())
                    if self._config.sheet_name:
                        try:
                            df = pd.read_excel(file_content, sheet_name=self._config.sheet_name)
                        except ValueError:
                            self._logger.warning(
                                "Worksheet '%s' not found in %s. Falling back to first sheet.",
                                self._config.sheet_name,
                                file_info.get("name", file_id),
                            )
                            df = pd.read_excel(file_content, sheet_name=0)
                    else:
                        df = pd.read_excel(file_content, sheet_name=0)
                    if not df.empty:
                        frames.append(df)
            except Exception as e:
                # Log error but continue with other files
                self._logger.warning("Could not load file %s: %s", file_info.get('name', file_info['id']), e)
                continue

        if not frames:
            raise RuntimeError(f"No data could be loaded from folder: {self._config.folder_url}")

        self._logger.info("Successfully loaded %d files, concatenating...", len(frames))
        combined = pd.concat(frames, ignore_index=True)
        self._logger.info("Combined dataset: %d rows x %d columns", len(combined), len(combined.columns))
        return {self._config.table_key: combined}

    def _extract_folder_id(self, url: str) -> str:
        """Extract folder ID from Google Drive URL."""
        # Handle different URL formats
        if "/folders/" in url:
            parts = url.split("/folders/")
            if len(parts) > 1:
                folder_id = parts[1].split("/")[0].split("?")[0]
                return folder_id
        raise ValueError(f"Invalid Google Drive folder URL: {url}")

    def _list_files_in_folder(self, drive_service, folder_id: str) -> List[Dict[str, str]]:
        """List all files in a Google Drive folder."""
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = (
                drive_service.files()
                .list(
                    q=query,
                    fields="files(id, name, mimeType)",
                    pageSize=1000,
                )
                .execute()
            )
            files = results.get("files", [])

            # Filter by Excel/Sheets files
            valid_mimes = [
                "application/vnd.google-apps.spreadsheet",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel",
            ]
            return [f for f in files if f.get("mimeType") in valid_mimes]
        except Exception as e:
            raise RuntimeError(f"Error listing files in folder: {e}")

    def _find_subfolder_id(self, drive_service, parent_folder_id: str, subfolder_name: str) -> str:
        """Find a subfolder by name under a parent folder."""
        try:
            query = (
                f"'{parent_folder_id}' in parents and trashed=false "
                "and mimeType='application/vnd.google-apps.folder'"
            )
            results = (
                drive_service.files()
                .list(
                    q=query,
                    fields="files(id, name)",
                    pageSize=1000,
                )
                .execute()
            )
            folders = results.get("files", [])
            matches = [f for f in folders if f.get("name") == subfolder_name]
            if not matches:
                raise FileNotFoundError(
                    f"Subfolder not found: '{subfolder_name}' in parent folder {self._config.folder_url}"
                )
            return matches[0]["id"]
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                raise
            raise RuntimeError(f"Error locating subfolder '{subfolder_name}': {e}")
