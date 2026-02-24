from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from market_report.observability.logging import get_logger


class GoogleDriveUploader:
    """Upload files to Google Drive folder."""

    def __init__(self):
        self._logger = get_logger(self.__class__.__name__)
        self._client: Optional[gspread.Client] = None
        self._drive_service = None
        self._creds: Optional[Credentials] = None

    def _get_client(self) -> tuple[gspread.Client, Credentials]:
        """Get authenticated Google Drive client."""
        if self._client is not None and self._drive_service is not None and self._creds is not None:
            return self._client, self._creds

        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        if service_account_file and Path(service_account_file).exists():
            creds = Credentials.from_service_account_file(
                service_account_file,
                scopes=[
                    "https://www.googleapis.com/auth/drive.file",
                    "https://www.googleapis.com/auth/drive",
                ],
            )
            self._client = gspread.authorize(creds)
            self._drive_service = build("drive", "v3", credentials=creds)
            self._creds = creds
            return self._client, creds

        raise RuntimeError(
            "Google Drive authentication failed. Set GOOGLE_SERVICE_ACCOUNT_FILE env var."
        )

    def apply_sheet_formats(
        self,
        file_id: str,
        sheet_name: str,
        column_formats: dict[str, dict[str, str]],
        bold_header: bool = True,
    ) -> None:
        """Apply number formats and optional header bolding to a Google Sheet."""
        _, creds = self._get_client()
        sheets_service = build("sheets", "v4", credentials=creds)

        meta = sheets_service.spreadsheets().get(
            spreadsheetId=file_id,
            fields="sheets(properties(sheetId,title,gridProperties(rowCount)))",
        ).execute()
        sheet_id = None
        row_count = None
        for sheet in meta.get("sheets", []):
            props = sheet.get("properties", {})
            if props.get("title") == sheet_name:
                sheet_id = props.get("sheetId")
                row_count = props.get("gridProperties", {}).get("rowCount", 0)
                break
        if sheet_id is None:
            self._logger.warning("Sheet '%s' not found for formatting.", sheet_name)
            return

        header = sheets_service.spreadsheets().values().get(
            spreadsheetId=file_id,
            range=f"{sheet_name}!1:1",
        ).execute().get("values", [[]])[0]

        requests = []
        for name, fmt in column_formats.items():
            if name not in header:
                continue
            col_idx = header.index(name)
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": row_count,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1,
                        },
                        "cell": {"userEnteredFormat": {"numberFormat": fmt}},
                        "fields": "userEnteredFormat.numberFormat",
                    }
                }
            )

        if bold_header and header:
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                        },
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat.bold",
                    }
                }
            )

        if not requests:
            return

        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=file_id, body={"requests": requests}
        ).execute()

    def upload_file(
        self,
        file_path: Path,
        folder_url: str,
        filename: Optional[str] = None,
        convert_to_sheets: bool = False,
    ) -> str:
        """Upload file to Google Drive folder.
        
        Args:
            file_path: Local path to file to upload
            folder_url: Google Drive folder URL
            filename: Optional filename override
            
        Returns:
            Google Drive file ID
        """
        client, creds = self._get_client()
        drive_service = self._drive_service

        folder_id = self._extract_folder_id(folder_url)
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        filename = filename or file_path.name
        sheet_name = filename
        if convert_to_sheets and filename.lower().endswith(".xlsx"):
            sheet_name = filename[:-5]

        self._logger.info("Uploading %s to Google Drive folder %s (folder_id: %s)", file_path, folder_url, folder_id)

        # Check if file already exists and delete it first
        try:
            names_to_check = {filename}
            if convert_to_sheets:
                names_to_check.add(sheet_name)
            for name in names_to_check:
                existing_files = (
                    drive_service.files()
                    .list(
                        q=f"name='{name}' and '{folder_id}' in parents and trashed=false",
                        fields="files(id, name)",
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                for existing_file in existing_files.get("files", []):
                    self._logger.info("Deleting existing file: %s (ID: %s)", existing_file["name"], existing_file["id"])
                    drive_service.files().delete(fileId=existing_file["id"], supportsAllDrives=True).execute()
        except Exception as e:
            self._logger.warning("Could not check for existing files: %s", e)

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
        }
        if convert_to_sheets:
            # We'll upload the XLSX and then copy/convert to Sheets to ensure conversion
            file_metadata["mimeType"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        media = MediaFileUpload(str(file_path), resumable=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        try:
            file = (
                drive_service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id",
                    supportsAllDrives=True,
                )
                .execute()
            )

            file_id = file.get("id")

            if convert_to_sheets:
                # Convert uploaded XLSX to Google Sheets via copy
                converted = (
                    drive_service.files()
                    .copy(
                        fileId=file_id,
                        body={
                            "name": sheet_name,
                            "parents": [folder_id],
                            "mimeType": "application/vnd.google-apps.spreadsheet",
                        },
                        fields="id",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
                converted_id = converted.get("id")
                # Remove original XLSX after conversion
                try:
                    drive_service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
                except Exception as e:
                    self._logger.warning("Could not delete original XLSX after conversion: %s", e)
                self._logger.info("File uploaded and converted to Sheets. File ID: %s", converted_id)
                return converted_id

            self._logger.info("File uploaded successfully. File ID: %s", file_id)
            return file_id
        except Exception as e:
            self._logger.error("Failed to upload file: %s", e)
            raise

    def _extract_folder_id(self, url: str) -> str:
        """Extract folder ID from Google Drive URL."""
        if "/" not in url and len(url) >= 10:
            return url
        if "/folders/" in url:
            parts = url.split("/folders/")
            if len(parts) > 1:
                folder_id = parts[1].split("/")[0].split("?")[0]
                return folder_id
        raise ValueError(f"Invalid Google Drive folder URL: {url}")
