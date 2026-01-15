from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuestionBankEntry:
    """Question bank row schema."""

    id: str
    category: str
    type: str
    question_text: str
    keyword: str


@dataclass(frozen=True)
class SurveyInfo:
    """Survey info schema."""

    client_name: str
    course_name: str
    manager: str
    date: str
    category: str
    survey_name: str


@dataclass(frozen=True)
class ResponseRecord:
    """Response record schema."""

    survey_id: str
    respondent_id: str
    question_id: str
    answer_value: str
