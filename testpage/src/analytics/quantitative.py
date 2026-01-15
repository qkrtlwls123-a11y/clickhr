from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass
class NPSResult:
    score: float
    promoters: float
    passives: float
    detractors: float
    total: int


DEFAULT_NPS_CATEGORIES = {"nps", "추천", "추천의향", "net promoter score"}


def _coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _safe_group_mean(df: pd.DataFrame, group_cols: list[str], score_col: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[*group_cols, "mean_score", "response_count"])
    grouped = (
        df.groupby(group_cols, dropna=False)[score_col]
        .agg(mean_score="mean", response_count="count")
        .reset_index()
    )
    return grouped


def attach_question_metadata(
    responses: pd.DataFrame,
    question_bank: pd.DataFrame | None,
    *,
    question_id_col: str = "question_id",
) -> pd.DataFrame:
    if question_bank is None or question_bank.empty:
        return responses.copy()
    bank = question_bank.copy()
    if "question_id" not in bank.columns and "id" in bank.columns:
        bank = bank.rename(columns={"id": "question_id"})
    if "category" not in bank.columns:
        return responses.copy()
    return responses.merge(bank[["question_id", "category"]], on=question_id_col, how="left")


def attach_dimension_metadata(
    responses: pd.DataFrame,
    metadata: pd.DataFrame | None,
    *,
    join_key: str = "survey_id",
    dimension_cols: Iterable[str] = ("course_name", "instructor_name", "round"),
) -> pd.DataFrame:
    if metadata is None or metadata.empty:
        return responses.copy()
    available_cols = [col for col in dimension_cols if col in metadata.columns]
    if join_key not in metadata.columns or not available_cols:
        return responses.copy()
    return responses.merge(metadata[[join_key, *available_cols]], on=join_key, how="left")


def calculate_satisfaction(
    responses: pd.DataFrame,
    *,
    group_cols: Iterable[str],
    score_col: str = "answer_value",
) -> pd.DataFrame:
    df = responses.copy()
    df[score_col] = _coerce_numeric(df[score_col])
    df = df.dropna(subset=[score_col])
    group_cols_list = list(group_cols)
    if not group_cols_list:
        avg_score = df[score_col].mean() if not df.empty else 0.0
        return pd.DataFrame({"mean_score": [avg_score], "response_count": [len(df)]})
    return _safe_group_mean(df, group_cols_list, score_col)


def calculate_nps(
    responses: pd.DataFrame,
    *,
    score_col: str = "answer_value",
    question_bank: pd.DataFrame | None = None,
    nps_question_ids: Iterable[str] | None = None,
    group_cols: Iterable[str] | None = None,
) -> pd.DataFrame:
    df = responses.copy()
    df[score_col] = _coerce_numeric(df[score_col])
    df = df.dropna(subset=[score_col])

    if nps_question_ids is not None:
        df = df[df["question_id"].isin(nps_question_ids)]
    elif question_bank is not None and not question_bank.empty:
        bank = question_bank.copy()
        if "question_id" not in bank.columns and "id" in bank.columns:
            bank = bank.rename(columns={"id": "question_id"})
        if "category" in bank.columns:
            nps_ids = bank[
                bank["category"].astype(str).str.lower().isin(DEFAULT_NPS_CATEGORIES)
            ]["question_id"].tolist()
            if nps_ids:
                df = df[df["question_id"].isin(nps_ids)]

    if df.empty:
        empty_cols = list(group_cols) if group_cols else []
        return pd.DataFrame(columns=[*empty_cols, "nps", "promoters", "passives", "detractors", "total"])

    def _compute_nps(series: pd.Series) -> NPSResult:
        total = series.count()
        promoters = (series >= 9).sum()
        passives = ((series >= 7) & (series <= 8)).sum()
        detractors = (series <= 6).sum()
        if total == 0:
            return NPSResult(score=0.0, promoters=0.0, passives=0.0, detractors=0.0, total=0)
        promoters_pct = promoters / total * 100
        detractors_pct = detractors / total * 100
        passives_pct = passives / total * 100
        score = promoters_pct - detractors_pct
        return NPSResult(
            score=score,
            promoters=promoters_pct,
            passives=passives_pct,
            detractors=detractors_pct,
            total=total,
        )

    group_cols_list = list(group_cols) if group_cols else []
    if group_cols_list:
        records = []
        for keys, group in df.groupby(group_cols_list, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            result = _compute_nps(group[score_col])
            record = dict(zip(group_cols_list, keys))
            record.update(
                {
                    "nps": result.score,
                    "promoters": result.promoters,
                    "passives": result.passives,
                    "detractors": result.detractors,
                    "total": result.total,
                }
            )
            records.append(record)
        return pd.DataFrame.from_records(records)

    result = _compute_nps(df[score_col])
    return pd.DataFrame(
        [
            {
                "nps": result.score,
                "promoters": result.promoters,
                "passives": result.passives,
                "detractors": result.detractors,
                "total": result.total,
            }
        ]
    )


def build_quantitative_snapshot(
    responses: pd.DataFrame,
    *,
    question_bank: pd.DataFrame | None = None,
    metadata: pd.DataFrame | None = None,
    course_col: str = "course_name",
    instructor_col: str = "instructor_name",
    round_col: str = "round",
) -> dict[str, pd.DataFrame]:
    enriched = attach_question_metadata(responses, question_bank)
    enriched = attach_dimension_metadata(
        enriched,
        metadata,
        dimension_cols=(course_col, instructor_col, round_col),
    )

    for col in (course_col, instructor_col, round_col):
        if col not in enriched.columns:
            enriched[col] = "미지정"
        enriched[col] = enriched[col].fillna("미지정")

    overall = calculate_satisfaction(enriched, group_cols=[])
    by_course = calculate_satisfaction(enriched, group_cols=[course_col])
    by_instructor = calculate_satisfaction(enriched, group_cols=[instructor_col])
    by_round = calculate_satisfaction(enriched, group_cols=[round_col])
    nps = calculate_nps(
        enriched,
        question_bank=question_bank,
        group_cols=[course_col, instructor_col, round_col],
    )

    return {
        "overall": overall,
        "by_course": by_course,
        "by_instructor": by_instructor,
        "by_round": by_round,
        "nps": nps,
    }
