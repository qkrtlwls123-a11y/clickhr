import json
import os
from collections import Counter
from urllib import request

# ... (PROMPT_TEMPLATE 및 _fallback_summary 함수는 그대로 둠) ...

def analyze_comments(comments, _key=None):
    api_key = _key or os.getenv("GEMINI_API_KEY")

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
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ]
        }
    ).encode("utf-8")

    # [수정됨] f-string을 사용하여 api_key 변수 값을 URL에 삽입
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
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
        # 에러 메시지를 좀 더 자세히 보기 위해 exc를 출력
        return {
            "status": "error",
            "message": f"Gemini 호출 실패: {exc}",
            "result": None,
        }

    candidates = response_data.get("candidates", [])
    if not candidates:
        # 안전장치: candidates가 비어있거나 차단(Blocked)되었을 경우 처리
        return {
            "status": "error",
            "message": "Gemini 응답에 결과가 없습니다 (필터링되었을 수 있음).",
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
