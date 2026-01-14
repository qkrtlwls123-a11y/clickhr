import json
import os
from collections import Counter
from urllib import request


PROMPT_TEMPLATE = """
다음은 직원 교육 만족도 설문에 대한 정성 코멘트입니다.
핵심 감정(긍정/부정/중립) 분포와 핵심 키워드 5개를 한국어로 요약하세요.
코멘트 목록:
{comments}
""".strip()


def _fallback_summary(comments):
    tokens = [
        token
        for comment in comments
        for token in comment.replace(".", " ").replace(",", " ").split()
        if len(token) > 1
    ]
    common = [word for word, _ in Counter(tokens).most_common(5)]
    return {
        "sentiment": "중립",
        "keywords": common,
        "summary": "간단 요약: 빈도 기반 키워드를 추출했습니다.",
    }


def analyze_comments(comments, _key=None):
    api_key = (_key or os.getenv("GEMINI_API_KEY", "")).strip()

    if not comments:
        return {
            "status": "error",
            "message": "코멘트가 비어 있습니다.",
            "result": None,
        }

    if not api_key:
        return {
            "status": "simulated",
            "message": "GEMINI_API_KEY가 없어 로컬 요약을 반환합니다.",
            "result": _fallback_summary(comments),
        }

    prompt = PROMPT_TEMPLATE.format(comments="\n".join(comments))
    payload = json.dumps(
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }
    ).encode("utf-8")
    print(f"--- DEBUG ---")
    print(f"API Key 길이: {len(api_key)}") # 키 길이가 이상하게 길면 공백이 있는 것
    print(f"요청 URL: {url}")            # URL 중간에 끊김이 없는지 확인
    print(f"-------------")
    req = request.Request(
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-1.5-flash-001:generateContent?key={api_key}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Gemini 호출 실패: {exc}",
            "result": None,
        }

    candidates = response_data.get("candidates", [])
    if not candidates:
        return {
            "status": "error",
            "message": "Gemini 응답에 결과가 없습니다.",
            "result": None,
        }

    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    result = {
        "sentiment": "-",
        "keywords": [],
        "summary": text.strip() or "요약 결과가 비어 있습니다.",
    }

    return {
        "status": "success",
        "message": "Gemini 분석 완료",
        "result": result,
    }
