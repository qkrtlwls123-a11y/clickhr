from __future__ import annotations

from datetime import datetime
import re
from typing import Iterable

STANDARD_COLUMN_MAP = {
    "성명": "user_name",
    "이름": "user_name",
    "name": "user_name",
    "Name": "user_name",
    "respondent": "respondent_id",
    "respondent id": "respondent_id",
    "respondent_id": "respondent_id",
    "survey id": "survey_id",
    "survey_id": "survey_id",
    "question id": "question_id",
    "question_id": "question_id",
    "answer": "answer_value",
    "answer_value": "answer_value",
    "응답": "answer_value",
}


def _normalize_column_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).lower()


def map_columns(df):
    mapping = {}
    for col in df.columns:
        normalized = _normalize_column_name(col)
        if normalized in STANDARD_COLUMN_MAP:
            mapping[col] = STANDARD_COLUMN_MAP[normalized]
    return df.rename(columns=mapping)


def mask_entities(text: str, course_name: str, instructor_name: str) -> str:
    masked = text
    if course_name:
        masked = masked.replace(course_name, "{{COURSE}}")
    if instructor_name:
        masked = masked.replace(instructor_name, "{{INSTRUCTOR}}")
    return masked


def clean_question_text(text: str) -> str:
    cleaned = re.sub(r"^[\d\W]+", "", text.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def split_raw_questions(raw_text: str) -> list[str]:
    lines = [line for line in raw_text.splitlines() if line.strip()]
    questions = []
    for line in lines:
        cleaned = clean_question_text(line)
        if cleaned:
            questions.append(cleaned)
    return questions


def levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i]
        for j, char_b in enumerate(b, start=1):
            insertions = prev_row[j] + 1
            deletions = current_row[j - 1] + 1
            substitutions = prev_row[j - 1] + (char_a != char_b)
            current_row.append(min(insertions, deletions, substitutions))
        prev_row = current_row
    return prev_row[-1]


def similarity_ratio(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    distance = levenshtein_distance(a, b)
    return 1 - (distance / max_len)


def match_questions(
    questions: Iterable[str],
    question_bank: Iterable[dict],
    existing_threshold: float = 0.92,
    similar_threshold: float = 0.78,
):
    results = []
    bank_list = list(question_bank)
    for question in questions:
        best_match = None
        best_score = 0.0
        for item in bank_list:
            score = similarity_ratio(question, item["question_text"])
            if score > best_score:
                best_score = score
                best_match = item
        if best_match and best_score >= existing_threshold:
            status = "existing"
        elif best_match and best_score >= similar_threshold:
            status = "similar"
        else:
            status = "new"
        results.append(
            {
                "status": status,
                "question": question,
                "match_text": best_match["question_text"] if best_match else "",
                "match_id": best_match["question_id"] if best_match else None,
                "score": round(best_score, 3),
            }
        )
    return results


def _next_question_id(existing_ids: Iterable[str]) -> str:
    numeric_ids = []
    for item in existing_ids:
        match = re.search(r"(\d+)$", item)
        if match:
            numeric_ids.append(int(match.group(1)))
    next_id = max(numeric_ids, default=0) + 1
    return f"QB-{next_id:03d}"


def update_question_bank(question_bank: list[dict], results: Iterable[dict]):
    updated_bank = [item.copy() for item in question_bank]
    index = {item["question_id"]: item for item in updated_bank}
    existing_ids = [item["question_id"] for item in updated_bank]

    new_count = 0
    merged_count = 0

    for result in results:
        if result["status"] == "new":
            new_id = _next_question_id(existing_ids)
            existing_ids.append(new_id)
            updated_bank.append(
                {
                    "question_id": new_id,
                    "question_text": result["question"],
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "merged_count": 0,
                }
            )
            new_count += 1
        else:
            match_id = result.get("match_id")
            if match_id and match_id in index:
                index[match_id]["merged_count"] = index[match_id].get(
                    "merged_count", 0
                ) + 1
                merged_count += 1

    return updated_bank, {"new": new_count, "merged": merged_count}
