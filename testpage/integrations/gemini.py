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
    # API 키 공백 제거
    api_key = (_key or os.getenv("GEMINI_API_KEY", "")).strip()

    if not comments:
        return {"status": "error", "message": "코멘트 없음", "result": None}

    if not api_key:
        return {
            "status": "simulated",
            "message": "API Key 없음 (로컬 요약)",
            "result": _fallback_summary(comments), # _fallback_summary 함수 필요
        }

    prompt = PROMPT_TEMPLATE.format(comments="\n".join(comments))
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    # [변경 1] 모델명을 curl 명령어와 동일하게 'gemini-2.0-flash'로 설정
    model_name = "gemini-2.0-flash"
    
    # URL에는 키를 포함하지 않음 (헤더로 보낼 것이기 때문)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    # [변경 2] API 키를 URL 파라미터가 아닌 '헤더'에 포함 (curl의 -H 옵션과 동일)
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key 
    }

    print(f"--- DEBUG ---")
    print(f"Model: {model_name}")
    print(f"Requesting URL: {url}")
    print(f"-------------")

    req = request.Request(
        url,
        data=payload,
        headers=headers, # 여기서 헤더 전달
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            
    except error.HTTPError as e:
        # HTTP 에러 (400, 404, 403 등) 상세 출력
        error_msg = f"HTTP Error {e.code}: {e.reason}"
        try:
            # 구글이 보내준 상세 에러 메시지가 있다면 읽어서 출력
            error_body = e.read().decode('utf-8')
            print(f"Google Error Details: {error_body}")
        except:
            pass
        return {
            "status": "error",
            "message": f"Gemini 호출 실패: {error_msg}",
            "result": None,
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Gemini 연결 실패: {exc}",
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
