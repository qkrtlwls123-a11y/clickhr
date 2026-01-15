from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StorageConfig:
    """Configuration for storage drivers."""

    backend: str
    sheet_id: str | None = None
    credentials_json: str | None = None
    credentials_path: str | None = None
    bigquery_project: str | None = None
    bigquery_dataset: str | None = None
