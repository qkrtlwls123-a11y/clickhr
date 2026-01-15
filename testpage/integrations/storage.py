from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pandas as pd

DEFAULT_QUESTION_BANK = pd.DataFrame(
    [
        {"question_id": "L-001", "text": "{{COURSE}} 과정에 대해 만족하십니까?", "category": "전략"},
        {"question_id": "L-002", "text": "{{INSTRUCTOR}} 강사의 강의는 어땠나요?", "category": "소통"},
        {"question_id": "L-003", "text": "강의 시간은 적절했나요?", "category": "운영"},
        {"question_id": "L-004", "text": "교육 시간 배분은 적절했나요?", "category": "운영"},
        {"question_id": "L-005", "text": "향후 추천할 의향이 있나요?", "category": "NPS"},
    ]
)

QUESTION_BANK_COLUMNS = ["question_id", "text", "category", "created_at", "updated_at"]
SURVEY_INFO_COLUMNS = [
    "survey_id",
    "title",
    "question_count",
    "created_at",
    "form_url",
    "status",
]
RESPONSES_COLUMNS = [
    "survey_id",
    "respondent_id",
    "question_id",
    "answer_value",
    "submitted_at",
]


class StorageBackend(Protocol):
    def load_question_bank(self) -> pd.DataFrame:
        ...

    def save_question_bank(self, question_bank: pd.DataFrame) -> None:
        ...

    def append_question_bank(self, question_bank: pd.DataFrame) -> None:
        ...

    def load_survey_info(self) -> pd.DataFrame:
        ...

    def append_survey_info(self, survey_info: pd.DataFrame) -> None:
        ...

    def load_responses(self) -> pd.DataFrame:
        ...

    def append_responses(self, responses: pd.DataFrame) -> None:
        ...


@dataclass
class StorageConfig:
    backend: str
    sheet_id: str | None = None
    credentials_json: str | None = None
    credentials_path: str | None = None
    bigquery_project: str | None = None
    bigquery_dataset: str | None = None


class GoogleSheetsStore:
    def __init__(self, config: StorageConfig) -> None:
        self.config = config

    def _get_credentials(self):
        from google.oauth2.service_account import Credentials

        if self.config.credentials_json:
            info = json.loads(self.config.credentials_json)
            return Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
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

    def _worksheet(self, title: str, columns: list[str]):
        sheet = self._open_sheet()
        try:
            worksheet = sheet.worksheet(title)
        except Exception:
            worksheet = sheet.add_worksheet(title=title, rows=1000, cols=max(len(columns), 5))
        existing_header = worksheet.row_values(1)
        if existing_header != columns:
            worksheet.update("A1", [columns])
        return worksheet

    def _load_table(self, title: str, columns: list[str]) -> pd.DataFrame:
        worksheet = self._worksheet(title, columns)
        records = worksheet.get_all_records()
        if not records:
            return pd.DataFrame(columns=columns)
        df = pd.DataFrame(records)
        return df.reindex(columns=columns)

    def _replace_table(self, title: str, columns: list[str], data: pd.DataFrame) -> None:
        worksheet = self._worksheet(title, columns)
        worksheet.clear()
        worksheet.update("A1", [columns])
        rows = data.reindex(columns=columns).fillna("").values.tolist()
        if rows:
            worksheet.update(f"A2", rows)

    def _append_rows(self, title: str, columns: list[str], data: pd.DataFrame) -> None:
        worksheet = self._worksheet(title, columns)
        rows = data.reindex(columns=columns).fillna("").values.tolist()
        if rows:
            worksheet.append_rows(rows)

    def load_question_bank(self) -> pd.DataFrame:
        return self._load_table("question_bank", QUESTION_BANK_COLUMNS)

    def save_question_bank(self, question_bank: pd.DataFrame) -> None:
        self._replace_table("question_bank", QUESTION_BANK_COLUMNS, question_bank)

    def append_question_bank(self, question_bank: pd.DataFrame) -> None:
        self._append_rows("question_bank", QUESTION_BANK_COLUMNS, question_bank)

    def load_survey_info(self) -> pd.DataFrame:
        return self._load_table("survey_info", SURVEY_INFO_COLUMNS)

    def append_survey_info(self, survey_info: pd.DataFrame) -> None:
        self._append_rows("survey_info", SURVEY_INFO_COLUMNS, survey_info)

    def load_responses(self) -> pd.DataFrame:
        return self._load_table("responses", RESPONSES_COLUMNS)

    def append_responses(self, responses: pd.DataFrame) -> None:
        self._append_rows("responses", RESPONSES_COLUMNS, responses)


class BigQueryStore:
    def __init__(self, config: StorageConfig) -> None:
        self.config = config

    def _client(self):
        from google.cloud import bigquery

        if not self.config.bigquery_project:
            raise ValueError("BigQuery project is not configured.")
        return bigquery.Client(project=self.config.bigquery_project)

    def _table_id(self, table_name: str) -> str:
        if not self.config.bigquery_dataset:
            raise ValueError("BigQuery dataset is not configured.")
        return f"{self.config.bigquery_project}.{self.config.bigquery_dataset}.{table_name}"

    def _load_table(self, table_name: str, columns: list[str]) -> pd.DataFrame:
        client = self._client()
        query = f"SELECT * FROM `{self._table_id(table_name)}`"
        df = client.query(query).to_dataframe()
        return df.reindex(columns=columns)

    def _append_rows(self, table_name: str, columns: list[str], data: pd.DataFrame) -> None:
        client = self._client()
        table_id = self._table_id(table_name)
        load_job = client.load_table_from_dataframe(
            data.reindex(columns=columns),
            table_id,
        )
        load_job.result()

    def _replace_table(self, table_name: str, columns: list[str], data: pd.DataFrame) -> None:
        client = self._client()
        table_id = self._table_id(table_name)
        job_config = client.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        load_job = client.load_table_from_dataframe(
            data.reindex(columns=columns),
            table_id,
            job_config=job_config,
        )
        load_job.result()

    def load_question_bank(self) -> pd.DataFrame:
        return self._load_table("question_bank", QUESTION_BANK_COLUMNS)

    def save_question_bank(self, question_bank: pd.DataFrame) -> None:
        self._replace_table("question_bank", QUESTION_BANK_COLUMNS, question_bank)

    def append_question_bank(self, question_bank: pd.DataFrame) -> None:
        self._append_rows("question_bank", QUESTION_BANK_COLUMNS, question_bank)

    def load_survey_info(self) -> pd.DataFrame:
        return self._load_table("survey_info", SURVEY_INFO_COLUMNS)

    def append_survey_info(self, survey_info: pd.DataFrame) -> None:
        self._append_rows("survey_info", SURVEY_INFO_COLUMNS, survey_info)

    def load_responses(self) -> pd.DataFrame:
        return self._load_table("responses", RESPONSES_COLUMNS)

    def append_responses(self, responses: pd.DataFrame) -> None:
        self._append_rows("responses", RESPONSES_COLUMNS, responses)


class LocalCSVStore:
    def __init__(self, base_path: str) -> None:
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def _file_path(self, name: str) -> str:
        return os.path.join(self.base_path, f"{name}.csv")

    def _load(self, name: str, columns: list[str]) -> pd.DataFrame:
        path = self._file_path(name)
        if not os.path.exists(path):
            return pd.DataFrame(columns=columns)
        df = pd.read_csv(path)
        return df.reindex(columns=columns)

    def _save(self, name: str, columns: list[str], data: pd.DataFrame) -> None:
        path = self._file_path(name)
        data.reindex(columns=columns).to_csv(path, index=False)

    def _append(self, name: str, columns: list[str], data: pd.DataFrame) -> None:
        existing = self._load(name, columns)
        merged = pd.concat([existing, data.reindex(columns=columns)], ignore_index=True)
        self._save(name, columns, merged)

    def load_question_bank(self) -> pd.DataFrame:
        return self._load("question_bank", QUESTION_BANK_COLUMNS)

    def save_question_bank(self, question_bank: pd.DataFrame) -> None:
        self._save("question_bank", QUESTION_BANK_COLUMNS, question_bank)

    def append_question_bank(self, question_bank: pd.DataFrame) -> None:
        self._append("question_bank", QUESTION_BANK_COLUMNS, question_bank)

    def load_survey_info(self) -> pd.DataFrame:
        return self._load("survey_info", SURVEY_INFO_COLUMNS)

    def append_survey_info(self, survey_info: pd.DataFrame) -> None:
        self._append("survey_info", SURVEY_INFO_COLUMNS, survey_info)

    def load_responses(self) -> pd.DataFrame:
        return self._load("responses", RESPONSES_COLUMNS)

    def append_responses(self, responses: pd.DataFrame) -> None:
        self._append("responses", RESPONSES_COLUMNS, responses)


def utc_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def build_storage_config() -> StorageConfig:
    return StorageConfig(
        backend=os.getenv("CLICKHR_STORAGE_BACKEND", "sheets"),
        sheet_id=os.getenv("CLICKHR_GSHEET_ID"),
        credentials_json=os.getenv("CLICKHR_GSHEET_CREDENTIALS_JSON"),
        credentials_path=os.getenv("CLICKHR_GSHEET_CREDENTIALS_PATH"),
        bigquery_project=os.getenv("CLICKHR_BQ_PROJECT"),
        bigquery_dataset=os.getenv("CLICKHR_BQ_DATASET"),
    )


def get_storage() -> StorageBackend:
    config = build_storage_config()
    backend = config.backend.lower()
    if backend == "bigquery":
        if config.bigquery_project and config.bigquery_dataset:
            return BigQueryStore(config)
        return LocalCSVStore(base_path=os.getenv("CLICKHR_LOCAL_STORE", "/workspace/clickhr/testpage/.store"))
    if backend == "sheets":
        if config.sheet_id and (config.credentials_json or config.credentials_path):
            return GoogleSheetsStore(config)
        return LocalCSVStore(base_path=os.getenv("CLICKHR_LOCAL_STORE", "/workspace/clickhr/testpage/.store"))
    return LocalCSVStore(base_path=os.getenv("CLICKHR_LOCAL_STORE", "/workspace/clickhr/testpage/.store"))


def standardize_question_bank(df: pd.DataFrame) -> pd.DataFrame:
    question_id = df["ID"] if "ID" in df.columns else df.get("question_id")
    text = df["문항"] if "문항" in df.columns else df.get("text")
    category = df["카테고리"] if "카테고리" in df.columns else df.get("category")
    output = pd.DataFrame(
        {
            "question_id": question_id,
            "text": text,
            "category": category,
        }
    )
    now = utc_now()
    output["created_at"] = df.get("created_at", now)
    output["updated_at"] = now
    output = output.dropna(subset=["question_id", "text"], how="any")
    return output.reindex(columns=QUESTION_BANK_COLUMNS)


def standardize_survey_info(df: pd.DataFrame) -> pd.DataFrame:
    output = df.reindex(columns=SURVEY_INFO_COLUMNS)
    return output


def standardize_responses(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    if "submitted_at" not in output.columns:
        output["submitted_at"] = utc_now()
    return output.reindex(columns=RESPONSES_COLUMNS)


def seed_question_bank(store: StorageBackend) -> pd.DataFrame:
    existing = store.load_question_bank()
    if not existing.empty:
        return existing
    seed = DEFAULT_QUESTION_BANK.copy()
    seed["created_at"] = utc_now()
    seed["updated_at"] = seed["created_at"]
    seed = seed.reindex(columns=QUESTION_BANK_COLUMNS)
    store.save_question_bank(seed)
    return seed
