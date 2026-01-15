from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence
from urllib.parse import parse_qs, urlparse

import pandas as pd

COLUMN_STANDARDIZATION_MAP: dict[str, list[str]] = {
    "user_name": ["성명", "이름", "Name", "name", "응답자", "응답자명"],
    "user_email": ["이메일", "Email", "E-mail", "메일"],
    "department": ["부서", "Department", "조직", "팀"],
    "course_name": ["과정명", "교육명", "Course", "Program", "교육 과정"],
    "instructor_name": ["강사명", "Instructor", "강사", "Trainer"],
    "submitted_at": ["응답일", "제출일", "Timestamp", "제출 시간", "응답 시간"],
    "question_text": ["문항", "질문", "Question", "항목"],
    "score": ["점수", "평점", "Score", "Rating", "응답"],
}


@dataclass(frozen=True)
class QuestionMatch:
    status: str
    original: str
    cleaned: str
    note: str
    match_id: str | int | None
    score: float


def load_raw_survey_data(source: str | bytes | io.BytesIO | pd.DataFrame, sheet_name: str | int = 0) -> pd.DataFrame:
    """Load Excel or Google Sheets data into a dataframe."""
    if isinstance(source, pd.DataFrame):
        return source.copy()

    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)

    if hasattr(source, "read"):
        return pd.read_excel(source, sheet_name=sheet_name)

    if isinstance(source, str):
        source = source.strip()
        if source.startswith("http"):
            url = _google_sheets_to_csv(source)
            return pd.read_csv(url)
        lower = source.lower()
        if lower.endswith((".xlsx", ".xls")):
            return pd.read_excel(source, sheet_name=sheet_name)
        return pd.read_csv(source)

    raise TypeError("Unsupported source type for survey data loading.")


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names using COLUMN_STANDARDIZATION_MAP."""
    normalized_map = _normalize_column_map(COLUMN_STANDARDIZATION_MAP)
    renamed = {}
    for col in df.columns:
        normalized = _normalize_column_name(str(col))
        if normalized in normalized_map:
            renamed[col] = normalized_map[normalized]
    return df.rename(columns=renamed)


def mask_proper_nouns(text: str, replacements: Mapping[str, str]) -> str:
    """Mask proper nouns based on replacement mapping."""
    masked = text
    for original, placeholder in replacements.items():
        if not original:
            continue
        masked = re.sub(re.escape(original), placeholder, masked)
    return masked


def classify_questions(
    questions: Iterable[str],
    question_bank: Sequence[Mapping[str, str]] | Sequence[str],
    course_name: str | None = None,
    instructor_name: str | None = None,
    existing_threshold: float = 0.95,
    similar_threshold: float = 0.8,
) -> list[QuestionMatch]:
    """Classify uploaded questions into existing/similar/new buckets."""
    replacements = {}
    if course_name:
        replacements[course_name] = "{{COURSE}}"
    if instructor_name:
        replacements[instructor_name] = "{{INSTRUCTOR}}"

    bank_records = _normalize_question_bank(question_bank)
    results: list[QuestionMatch] = []
    for question in questions:
        normalized = _normalize_text(question)
        masked = mask_proper_nouns(normalized, replacements) if replacements else normalized
        match_id, match_text, score = _find_best_match(masked, bank_records)

        if match_text and score >= existing_threshold:
            status = "existing"
            note = "기존 문항 일치 (자동 병합)"
        elif match_text and score >= similar_threshold:
            status = "similar"
            note = f"유사 문항 발견: '{match_text}'"
        else:
            status = "new"
            note = "DB에 없는 신규 문항 (등록 필요)"

        results.append(
            QuestionMatch(
                status=status,
                original=question,
                cleaned=masked,
                note=note,
                match_id=match_id,
                score=score,
            )
        )
    return results


def _normalize_column_map(mapping: Mapping[str, Sequence[str]]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for standard, aliases in mapping.items():
        normalized[_normalize_column_name(standard)] = standard
        for alias in aliases:
            normalized[_normalize_column_name(alias)] = standard
    return normalized


def _normalize_column_name(name: str) -> str:
    return re.sub(r"\s+", "", name.strip().lower())


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"\d+", " ", text)
    cleaned = re.sub(r"[^\w\s가-힣]", " ", cleaned)
    cleaned = cleaned.replace("_", " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def _normalize_question_bank(question_bank: Sequence[Mapping[str, str]] | Sequence[str]) -> list[tuple[str | int | None, str]]:
    normalized: list[tuple[str | int | None, str]] = []
    for entry in question_bank:
        if isinstance(entry, str):
            normalized.append((None, entry))
        else:
            normalized.append((entry.get("id") or entry.get("question_id"), entry.get("text", "")))
    return normalized


def _find_best_match(cleaned: str, question_bank: Sequence[tuple[str | int | None, str]]) -> tuple[str | int | None, str | None, float]:
    best_match = None
    best_score = 0.0
    best_id = None
    for question_id, text in question_bank:
        normalized_question = _normalize_text(text)
        score = _similarity_ratio(cleaned, normalized_question)
        if score > best_score:
            best_score = score
            best_match = text
            best_id = question_id
    return best_id, best_match, best_score


def _levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        curr_row = [i]
        for j, char_b in enumerate(b, start=1):
            insertions = prev_row[j] + 1
            deletions = curr_row[j - 1] + 1
            substitutions = prev_row[j - 1] + (char_a != char_b)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def _similarity_ratio(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    distance = _levenshtein_distance(a, b)
    max_len = max(len(a), len(b))
    return 1 - (distance / max_len) if max_len else 0.0


def _google_sheets_to_csv(url: str) -> str:
    if "docs.google.com" not in url:
        return url
    parsed = urlparse(url)
    if "spreadsheets" not in parsed.path:
        return url
    sheet_id = parsed.path.split("/")[3] if len(parsed.path.split("/")) > 3 else ""
    query = parse_qs(parsed.query)
    gid = query.get("gid", [None])[0]
    if sheet_id:
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        if gid:
            export_url += f"&gid={gid}"
        return export_url
    return url
