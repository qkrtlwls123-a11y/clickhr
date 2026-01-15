from __future__ import annotations

import json
import os
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any
from urllib import error, request


PROMPT_TEMPLATE = """
다음은 직원 교육 만족도 설문에 대한 정성 코멘트입니다.
핵심 감정(긍정/부정/중립)과 키워드 5개, 2~3문장 요약을 JSON으로 작성하세요.
반드시 아래 JSON 포맷을 따르세요.

{
  "sentiment": "긍정/부정/중립",
  "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
  "summary": "요약 문장"
}

코멘트 목록:
{comments}
""".strip()


@dataclass
class SummaryResult:
    sentiment: str
    keywords: list[str]
    summary: str


def _fallback_summary(comments: list[str]) -> SummaryResult:
    tokens = [
        token
        for comment in comments
        for token in comment.replace(".", " ").replace(",", " ").split()
        if len(token) > 1
    ]
    common = [word for word, _ in Counter(tokens).most_common(5)]
    return SummaryResult(
        sentiment="중립",
        keywords=common,
        summary="빈도 기반 키워드로 요약했습니다.",
    )


def _parse_json_response(text: str) -> SummaryResult | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    sentiment = data.get("sentiment")
    keywords = data.get("keywords")
    summary = data.get("summary")
    if not isinstance(sentiment, str) or not isinstance(summary, str) or not isinstance(keywords, list):
        return None
    keywords = [str(item) for item in keywords if item]
    return SummaryResult(sentiment=sentiment, keywords=keywords, summary=summary)


def summarize_comments(comments: list[str], api_key: str | None = None) -> dict[str, Any]:
    clean_comments = [comment.strip() for comment in comments if comment and comment.strip()]
    if not clean_comments:
        return {"status": "error", "message": "코멘트 없음", "result": None}

    api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    if not api_key:
        fallback = _fallback_summary(clean_comments)
        return {
            "status": "simulated",
            "message": "API Key 없음 (로컬 요약)",
            "result": {
                "sentiment": fallback.sentiment,
                "keywords": fallback.keywords,
                "summary": fallback.summary,
            },
        }

    prompt = PROMPT_TEMPLATE.format(comments="\n".join(clean_comments))
    payload_dict = {"contents": [{"parts": [{"text": prompt}]}]}
    payload = json.dumps(payload_dict).encode("utf-8")

    model_name = "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    headers = {"Content-Type": "application/json", "X-goog-api-key": api_key}

    max_retries = 2
    response_data: dict[str, Any] | None = None

    for attempt in range(max_retries + 1):
        try:
            req = request.Request(url, data=payload, headers=headers, method="POST")
            with request.urlopen(req, timeout=30) as response:
                response_body = response.read().decode("utf-8")
                response_data = json.loads(response_body)
                break
        except error.HTTPError as exc:
            error_details = exc.read().decode("utf-8")
            if exc.code == 429:
                time.sleep(3)
                continue
            if exc.code == 400:
                return {
                    "status": "error",
                    "message": f"요청 형식 오류 (HTTP 400): {error_details}",
                    "result": None,
                }
            if exc.code == 403:
                return {
                    "status": "error",
                    "message": "API 키 권한 없음 (HTTP 403).",
                    "result": None,
                }
            return {
                "status": "error",
                "message": f"API 호출 에러 (HTTP {exc.code})",
                "result": None,
            }
        except Exception as exc:  # pragma: no cover - network errors
            return {
                "status": "error",
                "message": f"연결 실패: {exc}",
                "result": None,
            }
    if response_data is None:
        return {
            "status": "error",
            "message": "재시도 횟수 초과 (서버 혼잡 또는 할당량 부족)",
            "result": None,
        }

    candidates = response_data.get("candidates", [])
    if not candidates:
        return {
            "status": "error",
            "message": "응답이 차단되었습니다 (Safety Filter).",
            "result": None,
        }

    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    parsed = _parse_json_response(text)
    if not parsed:
        fallback = _fallback_summary(clean_comments)
        return {
            "status": "success",
            "message": "응답 파싱 실패로 로컬 요약을 사용했습니다.",
            "result": {
                "sentiment": fallback.sentiment,
                "keywords": fallback.keywords,
                "summary": fallback.summary,
            },
        }

    return {
        "status": "success",
        "message": "분석 완료",
        "result": {
            "sentiment": parsed.sentiment,
            "keywords": parsed.keywords,
            "summary": parsed.summary,
        },
    }
