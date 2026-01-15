from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from .config import StorageConfig
from .drivers import BigQueryDriver


@dataclass(frozen=True)
class BigQueryAdapter(BigQueryDriver):
    """Concrete BigQuery implementation for phase 2 usage."""

    config: StorageConfig

    def _client(self):
        from google.cloud import bigquery

        if not self.config.bigquery_project:
            raise ValueError("BigQuery project is not configured.")
        return bigquery.Client(project=self.config.bigquery_project)

    def _table_id(self, table_name: str) -> str:
        if not self.config.bigquery_dataset:
            raise ValueError("BigQuery dataset is not configured.")
        return f"{self.config.bigquery_project}.{self.config.bigquery_dataset}.{table_name}"

    def query_table(self, table_name: str, columns: Sequence[str]) -> pd.DataFrame:
        client = self._client()
        query = f"SELECT * FROM `{self._table_id(table_name)}`"
        df = client.query(query).to_dataframe()
        return df.reindex(columns=list(columns))

    def append_rows(self, table_name: str, columns: Sequence[str], data: pd.DataFrame) -> None:
        client = self._client()
        table_id = self._table_id(table_name)
        load_job = client.load_table_from_dataframe(
            data.reindex(columns=list(columns)),
            table_id,
        )
        load_job.result()

    def overwrite_table(self, table_name: str, columns: Sequence[str], data: pd.DataFrame) -> None:
        client = self._client()
        table_id = self._table_id(table_name)
        job_config = client.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        load_job = client.load_table_from_dataframe(
            data.reindex(columns=list(columns)),
            table_id,
            job_config=job_config,
        )
        load_job.result()
