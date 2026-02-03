from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

from market_report.config.schemas import GoogleSheetsConfig
from market_report.ports.data_source import DataSource


class GoogleSheetsDataSource(DataSource):
    """Load Google Sheets data using Google Sheets API."""

    def __init__(self, config: GoogleSheetsConfig):
        self._config = config
        self._client: Optional[gspread.Client] = None

    def _get_client(self) -> gspread.Client:
        """Get authenticated Google Sheets client."""
        if self._client is not None:
            return self._client

        # Try service account credentials first
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        if service_account_file and Path(service_account_file).exists():
            creds = Credentials.from_service_account_file(
                service_account_file,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive.readonly"],
            )
            self._client = gspread.authorize(creds)
            return self._client

        # Fallback to OAuth2 if service account not available
        # This requires user to authenticate once
        try:
            self._client = gspread.service_account()
            return self._client
        except Exception:
            # If OAuth2 fails, try local CSV fallback
            if self._config.local_csv_dir:
                return None
            raise RuntimeError(
                "Google Sheets authentication failed. Set GOOGLE_SERVICE_ACCOUNT_FILE env var "
                "or configure OAuth2 credentials. See: https://gspread.readthedocs.io/en/latest/oauth2.html"
            )

    def load(self) -> Dict[str, pd.DataFrame]:
        """Load data from Google Sheets or fallback to local CSV."""
        # Try local CSV first if configured (for testing/development)
        if self._config.local_csv_dir:
            return self._load_from_local_csv(Path(self._config.local_csv_dir))

        # Load from Google Sheets API
        client = self._get_client()
        if client is None:
            # Fallback to CSV if client couldn't be created
            if self._config.local_csv_dir:
                return self._load_from_local_csv(Path(self._config.local_csv_dir))
            raise RuntimeError("Unable to connect to Google Sheets")

        tables: Dict[str, pd.DataFrame] = {}
        try:
            spreadsheet = client.open_by_key(self._config.spreadsheet_id)
        except Exception as e:
            raise FileNotFoundError(f"Unable to open Google Sheet with ID '{self._config.spreadsheet_id}': {e}")

        for tab_name in self._config.tabs:
            try:
                worksheet = spreadsheet.worksheet(tab_name)
                records = worksheet.get_all_records()
                if records:
                    tables[tab_name] = pd.DataFrame(records)
                else:
                    tables[tab_name] = pd.DataFrame()
            except gspread.exceptions.WorksheetNotFound:
                raise FileNotFoundError(f"Tab '{tab_name}' not found in spreadsheet")
            except Exception as e:
                raise RuntimeError(f"Error loading tab '{tab_name}': {e}")

        return tables

    def _load_from_local_csv(self, folder: Path) -> Dict[str, pd.DataFrame]:
        """Fallback: load from local CSV files (for testing/development)."""
        tables: Dict[str, pd.DataFrame] = {}
        for tab in self._config.tabs:
            csv_path = folder / f"{tab}.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing CSV fixture for tab '{tab}': {csv_path}")
            tables[tab] = pd.read_csv(csv_path)
        return tables
