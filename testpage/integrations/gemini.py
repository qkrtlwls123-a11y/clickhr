import json
import os
from collections import Counter
from urllib import request, error

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

def _send_request(url, payload):
    """실제 HTTP 요청을 보내는 내부 함수"""
    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))

def analyze_comments(comments, _key=None):
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
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}]
    }).encode("utf-8")

    # 시도할 모델 리스트 (순서대로 시도)
    # 1. Flash (빠름) -> 2. Pro (범용) -> 3. 1.0 Pro (구버전 호환)
    models_to_try = ["gemini-1.5-flash", "gemini-pro", "gemini-1.0-pro"]
    
    last_error = None
    response_data = None

    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            print(f"--- 시도 중: {model_name} ---") # 디버깅용
            
            response_data = _send_request(url, payload)
            
            # 성공하면 반복문 탈출
            print(f"--- 성공: {model_name} ---")
            break 
            
        except error.HTTPError as e:
            print(f"실패 ({model_name}): HTTP {e.code} - {e.reason}")
            last_error = f"HTTP {e.code}"
            # 404(모델 없음)나 400(요청 오류)이면 다음 모델 시도
            if e.code in [404, 400]:
                continue
            else:
                break # 403(권한 없음) 등은 키 문제이므로 중단
        except Exception as e:
            print(f"실패 ({model_name}): {e}")
            last_error = str(e)
            continue

    # 모든 모델 시도 후에도 실패했다면 에러 반환
    if not response_data:
        return {
            "status": "error",
            "message": f"모든 모델 호출 실패 (마지막 에러: {last_error})",
            "result": None,
        }

    candidates = response_data.get("candidates", [])
    if not candidates:
        return {
            "status": "error",
            "message": "응답은 받았으나 내용이 없습니다 (Safety Filter).",
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
