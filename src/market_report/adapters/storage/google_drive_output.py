from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class GoogleDriveOutput:
    """Upload files to a Google Drive folder."""

    def __init__(self, folder_url: str, convert_to_sheets: bool = False):
        self._folder_url = folder_url
        self._convert = convert_to_sheets

    def upload(self, file_path: Path, filename: str | None = None) -> Dict[str, str]:
        creds = self._get_credentials()
        drive_service = build("drive", "v3", credentials=creds)
        folder_id = self._extract_folder_id(self._folder_url)

        metadata = {
            "name": filename or file_path.name,
            "parents": [folder_id],
        }
        if self._convert:
            metadata["mimeType"] = "application/vnd.google-apps.spreadsheet"

        media = MediaFileUpload(str(file_path), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        result = (
            drive_service.files()
            .create(body=metadata, media_body=media, fields="id, name, webViewLink")
            .execute()
        )
        return {
            "id": result.get("id", ""),
            "name": result.get("name", ""),
            "webViewLink": result.get("webViewLink", ""),
        }

    def _get_credentials(self) -> Credentials:
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        if not service_account_file or not Path(service_account_file).exists():
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_FILE not set or file not found.")
        return Credentials.from_service_account_file(
            service_account_file,
            scopes=["https://www.googleapis.com/auth/drive"],
        )

    @staticmethod
    def _extract_folder_id(url: str) -> str:
        if "/folders/" in url:
            parts = url.split("/folders/")
            if len(parts) > 1:
                return parts[1].split("/")[0].split("?")[0]
        raise ValueError(f"Invalid Google Drive folder URL: {url}")
