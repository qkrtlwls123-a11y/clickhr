from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .drivers import StorageTable, TabularDriver


QUESTION_BANK_TABLE = StorageTable(
    name="question_bank",
    columns=["id", "category", "type", "question_text", "keyword"],
)
SURVEY_INFO_TABLE = StorageTable(
    name="survey_info",
    columns=["client_name", "course_name", "manager", "date", "category", "survey_name"],
)
RESPONSES_TABLE = StorageTable(
    name="responses",
    columns=["survey_id", "respondent_id", "question_id", "answer_value"],
)


@dataclass
class StorageRepository:
    """CRUD access layer for survey storage."""

    driver: TabularDriver

    def list_question_bank(self) -> pd.DataFrame:
        return self.driver.read_table(QUESTION_BANK_TABLE.name, QUESTION_BANK_TABLE.columns)

    def create_question_bank(self, rows: Iterable[dict]) -> None:
        df = pd.DataFrame(list(rows))
        self.driver.append_rows(QUESTION_BANK_TABLE.name, QUESTION_BANK_TABLE.columns, df)

    def replace_question_bank(self, rows: Iterable[dict]) -> None:
        df = pd.DataFrame(list(rows))
        self.driver.write_table(QUESTION_BANK_TABLE.name, QUESTION_BANK_TABLE.columns, df)

    def list_survey_info(self) -> pd.DataFrame:
        return self.driver.read_table(SURVEY_INFO_TABLE.name, SURVEY_INFO_TABLE.columns)

    def create_survey_info(self, rows: Iterable[dict]) -> None:
        df = pd.DataFrame(list(rows))
        self.driver.append_rows(SURVEY_INFO_TABLE.name, SURVEY_INFO_TABLE.columns, df)

    def replace_survey_info(self, rows: Iterable[dict]) -> None:
        df = pd.DataFrame(list(rows))
        self.driver.write_table(SURVEY_INFO_TABLE.name, SURVEY_INFO_TABLE.columns, df)

    def list_responses(self) -> pd.DataFrame:
        return self.driver.read_table(RESPONSES_TABLE.name, RESPONSES_TABLE.columns)

    def create_responses(self, rows: Iterable[dict]) -> None:
        df = pd.DataFrame(list(rows))
        self.driver.append_rows(RESPONSES_TABLE.name, RESPONSES_TABLE.columns, df)

    def replace_responses(self, rows: Iterable[dict]) -> None:
        df = pd.DataFrame(list(rows))
        self.driver.write_table(RESPONSES_TABLE.name, RESPONSES_TABLE.columns, df)
