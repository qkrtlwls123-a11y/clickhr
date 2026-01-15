from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import pandas as pd


class TabularDriver(Protocol):
    """Generic tabular driver for sheet-like storage."""

    def read_table(self, table_name: str, columns: Sequence[str]) -> pd.DataFrame:
        ...

    def write_table(self, table_name: str, columns: Sequence[str], data: pd.DataFrame) -> None:
        ...

    def append_rows(self, table_name: str, columns: Sequence[str], data: pd.DataFrame) -> None:
        ...


class BigQueryDriver(Protocol):
    """Abstract BigQuery driver interface for phase 2 expansion."""

    def query_table(self, table_name: str, columns: Sequence[str]) -> pd.DataFrame:
        ...

    def append_rows(self, table_name: str, columns: Sequence[str], data: pd.DataFrame) -> None:
        ...

    def overwrite_table(self, table_name: str, columns: Sequence[str], data: pd.DataFrame) -> None:
        ...


@dataclass(frozen=True)
class StorageTable:
    name: str
    columns: Sequence[str]
