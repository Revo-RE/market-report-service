#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pipeline for all city folders in Drive.")
    parser.add_argument(
        "--config",
        default="configs/projects/consolidado_drive.json",
        help="Path to base project config JSON",
    )
    parser.add_argument(
        "--default-config",
        default="configs/projects/default.json",
        help="Path to default config JSON",
    )
    parser.add_argument(
        "--prefix",
        default="Historicos ",
        help="Folder prefix to detect city folders (default: 'Historicos ')",
    )
    parser.add_argument(
        "--root-subfolder",
        default="",
        help="Optional subfolder inside the root Drive folder (default: none)",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Optional list of city names to run (e.g., Guadalajara LosCabos)",
    )
    return parser.parse_args()


CITY = "Ciudad de Mexico"


def _extract_folder_id(url: str) -> str:
    if "/folders/" in url:
        parts = url.split("/folders/")
        if len(parts) > 1:
            return parts[1].split("/")[0].split("?")[0]
    raise ValueError(f"Invalid Google Drive folder URL: {url}")


def _get_drive_service() -> object:
    cred_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or "credentials.json"
    if not Path(cred_path).exists():
        raise FileNotFoundError("Missing Google credentials.json or GOOGLE_SERVICE_ACCOUNT_FILE.")
    creds = Credentials.from_service_account_file(
        cred_path,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    return build("drive", "v3", credentials=creds)


def _list_subfolders(drive_service, parent_folder_id: str) -> list[dict[str, str]]:
    query = (
        f"'{parent_folder_id}' in parents and trashed=false "
        "and (mimeType='application/vnd.google-apps.folder' "
        "or mimeType='application/vnd.google-apps.shortcut')"
    )
    results = (
        drive_service.files()
            .list(
                q=query,
                fields="files(id, name, mimeType, shortcutDetails)",
                pageSize=1000,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="allDrives",
            )
            .execute()
    )
    folders = []
    for item in results.get("files", []):
        if item.get("mimeType") == "application/vnd.google-apps.shortcut":
            target_id = (item.get("shortcutDetails") or {}).get("targetId")
            if target_id:
                folders.append({"id": target_id, "name": item.get("name", "")})
        else:
            folders.append(item)
    return folders

def _list_data_files(drive_service, folder_id: str) -> list[dict[str, str]]:
    query = f"'{folder_id}' in parents and trashed=false"
    results = (
        drive_service.files()
        .list(
            q=query,
            fields="files(id, name, mimeType)",
            pageSize=1000,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
        )
        .execute()
    )
    files = results.get("files", [])
    valid_mimes = [
        "application/vnd.google-apps.spreadsheet",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ]
    return [f for f in files if f.get("mimeType") in valid_mimes]


def _load_base_config(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def main() -> int:
    args = parse_args()

    base_cfg = _load_base_config(args.config)
    folder_url = base_cfg.get("google_drive_folder", {}).get("folder_url")
    if not folder_url:
        raise ValueError("google_drive_folder.folder_url missing in config.")

    drive_service = _get_drive_service()
    parent_folder_id = _extract_folder_id(folder_url)
    folders = _list_subfolders(drive_service, parent_folder_id)
    if args.root_subfolder:
        matches = [f for f in folders if f.get("name") == args.root_subfolder]
        if matches:
            parent_folder_id = matches[0]["id"]
            folders = _list_subfolders(drive_service, parent_folder_id)
        else:
            print(f"⚠️  Root subfolder '{args.root_subfolder}' not found. Using root folder.")

    prefix = args.prefix
    candidates = [f for f in folders if f.get("name", "").startswith(prefix)]
    # Force a single city run (manual selection).
    candidates = [f for f in candidates if f["name"].replace(prefix, "") == CITY]

    if not candidates:
        print("No city folders found.")
        return 1

    for folder in sorted(candidates, key=lambda f: f["name"]):
        city = folder["name"].replace(prefix, "")
        data_files = _list_data_files(drive_service, folder["id"])
        if not data_files:
            print(f"⏭️  Skipping {city}: no files found in folder")
            continue
        print(f"\n=== Running pipeline for {city} ===")
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{Path.cwd() / 'src'}"
        env["SKIP_LOCAL_OUTPUTS"] = "1"
        cmd = [
            sys.executable,
            "run.py",
            "--config",
            args.config,
            "--default-config",
            args.default_config,
            "--project",
            city,
        ]
        result = subprocess.run(cmd, env=env, check=False)
        if result.returncode != 0:
            print(f"❌ Failed for {city} (exit {result.returncode})")
        else:
            print(f"✅ Done for {city}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
