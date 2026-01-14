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
    # API 키 공백 제거
    api_key = (_key or os.getenv("GEMINI_API_KEY", "")).strip()

    if not comments:
        return {"status": "error", "message": "코멘트 없음", "result": None}

    if not api_key:
        return {
            "status": "simulated",
            "message": "API Key 없음 (로컬 요약)",
            "result": _fallback_summary(comments),
        }

    prompt = PROMPT_TEMPLATE.format(comments="\n".join(comments))
    payload = json.dumps(
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }
    ).encode("utf-8")

    # [핵심 수정] 모델명을 'gemini-1.5-flash'로 변경 (가장 안정적)
    # 만약 그래도 404가 뜨면 'gemini-pro'로 바꿔보세요.
    model_name = "gemini-1.5-flash"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    print(f"--- DEBUG ---")
    print(f"Model: {model_name}")
    print(f"URL Start: {url[:50]}...") # 보안을 위해 키 부분은 숨김
    print(f"-------------")

    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as response:
            if response.status == 200:
                response_data = json.loads(response.read().decode("utf-8"))
            else:
                 return {"status": "error", "message": f"HTTP Error {response.status}", "result": None}
                 
    except Exception as exc:
        # 에러가 나면 구체적인 메시지를 반환
        return {
            "status": "error",
            "message": f"Gemini 호출 실패 ({exc}) - URL 확인 필요",
            "result": None,
        }

    candidates = response_data.get("candidates", [])
    if not candidates:
        return {
            "status": "error",
            "message": "Gemini 결과 없음 (Safety Filter 등)",
            "result": None,
        }

    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    
    return {
        "status": "success",
        "message": "분석 완료",
        "result": {
            "sentiment": "-",
            "keywords": [],
            "summary": text.strip()
        },
    }
