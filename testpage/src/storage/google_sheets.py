from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from .config import StorageConfig
from .drivers import TabularDriver


@dataclass(frozen=True)
class GoogleSheetsDriver(TabularDriver):
    config: StorageConfig

    def _get_credentials(self):
        from google.oauth2.service_account import Credentials

        if self.config.credentials_json:
            info = json.loads(self.config.credentials_json)
            return Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
        if self.config.credentials_path:
            return Credentials.from_service_account_file(
                self.config.credentials_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
        raise ValueError("Google Sheets credentials are not configured.")

    def _open_sheet(self):
        if not self.config.sheet_id:
            raise ValueError("Google Sheets ID is not configured.")
        import gspread

        credentials = self._get_credentials()
        client = gspread.authorize(credentials)
        return client.open_by_key(self.config.sheet_id)

    def _worksheet(self, title: str, columns: Sequence[str]):
        sheet = self._open_sheet()
        try:
            worksheet = sheet.worksheet(title)
        except Exception:
            worksheet = sheet.add_worksheet(title=title, rows=1000, cols=max(len(columns), 5))
        existing_header = worksheet.row_values(1)
        if list(existing_header) != list(columns):
            worksheet.update("A1", [list(columns)])
        return worksheet

    def read_table(self, table_name: str, columns: Sequence[str]) -> pd.DataFrame:
        worksheet = self._worksheet(table_name, columns)
        records = worksheet.get_all_records()
        if not records:
            return pd.DataFrame(columns=list(columns))
        df = pd.DataFrame(records)
        return df.reindex(columns=list(columns))

    def write_table(self, table_name: str, columns: Sequence[str], data: pd.DataFrame) -> None:
        worksheet = self._worksheet(table_name, columns)
        worksheet.clear()
        worksheet.update("A1", [list(columns)])
        rows = data.reindex(columns=list(columns)).fillna("").values.tolist()
        if rows:
            worksheet.update("A2", rows)

    def append_rows(self, table_name: str, columns: Sequence[str], data: pd.DataFrame) -> None:
        worksheet = self._worksheet(table_name, columns)
        rows = data.reindex(columns=list(columns)).fillna("").values.tolist()
        if rows:
            worksheet.append_rows(rows)
