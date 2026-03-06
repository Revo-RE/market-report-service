from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload


class GoogleDriveAuditStore:
    """Store and fetch audit JSON files from a Google Drive folder."""

    def __init__(self, folder_url: str):
        self._folder_id = self._extract_folder_id(folder_url)
        self._service = self._get_drive_service()

    @staticmethod
    def _extract_folder_id(url: str) -> str:
        if "/folders/" in url:
            parts = url.split("/folders/")
            if len(parts) > 1:
                return parts[1].split("/")[0].split("?")[0]
        raise ValueError(f"Invalid Google Drive folder URL: {url}")

    @staticmethod
    def _get_drive_service():
        cred_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or "credentials.json"
        if not Path(cred_path).exists():
            raise FileNotFoundError("Missing Google credentials.json or GOOGLE_SERVICE_ACCOUNT_FILE.")
        creds = Credentials.from_service_account_file(
            cred_path,
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/drive.file",
            ],
        )
        return build("drive", "v3", credentials=creds)

    def _find_file_id(self, name: str) -> Optional[str]:
        query = (
            f"'{self._folder_id}' in parents and trashed=false and name='{name}'"
        )
        results = (
            self._service.files()
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
        if not files:
            return None
        return files[0]["id"]

    def download_json(self, name: str) -> Optional[Dict[str, Any]]:
        file_id = self._find_file_id(name)
        if not file_id:
            return None
        request = self._service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        return json.loads(buffer.read().decode("utf-8"))

    def upload_json(self, name: str, payload: Dict[str, Any]) -> str:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype="application/json", resumable=False)
        file_id = self._find_file_id(name)
        if file_id:
            updated = (
                self._service.files()
                .update(
                    fileId=file_id,
                    media_body=media,
                    supportsAllDrives=True,
                    fields="id",
                )
                .execute()
            )
            return updated["id"]
        created = (
            self._service.files()
            .create(
                body={"name": name, "parents": [self._folder_id]},
                media_body=media,
                supportsAllDrives=True,
                fields="id",
            )
            .execute()
        )
        return created["id"]
