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
    # [수정 1] API 키 공백 제거 (안전 장치)
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

    # [수정 2] URL 변수를 먼저 정의 (순서 중요!)
    # 모델명은 가장 안정적인 최신 별칭인 'gemini-1.5-flash' 사용
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    # [수정 3] URL 정의 후 디버깅 출력 (이제 에러가 나지 않습니다)
    print(f"--- DEBUG ---")
    print(f"API Key 길이: {len(api_key)}") 
    print(f"요청 URL: {url}")
    print(f"-------------")

    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        # 에러 발생 시 로그에 남기기 위해 메시지 상세화
        return {
            "status": "error",
            "message": f"Gemini 호출 실패: {exc}",
            "result": None,
        }

    candidates = response_data.get("candidates", [])
    if not candidates:
        return {
            "status": "error",
            "message": "Gemini 응답에 결과가 없습니다 (Safety Filter 등).",
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
