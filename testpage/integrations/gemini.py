import json
import os
import time
from collections import Counter
from urllib import request, error

# --- [수정] 프롬프트: 명확한 JSON 구조 요청 ---
PROMPT_TEMPLATE = """
다음은 직원 교육 만족도 설문에 대한 정성 코멘트입니다.
전체적인 핵심 감정(긍정/부정/중립) 하나와, 가장 많이 언급된 핵심 키워드 5개를 뽑아주세요.

반드시 다음 JSON 형식으로만 답변하세요:
{
  "sentiment": "긍정",
  "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
  "summary": "전체 내용을 3문장으로 요약한 텍스트"
}

코멘트 목록:
{comments}
""".strip()

# --- [보조] 로컬 분석 함수 ---
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
        "summary": "API 키가 없거나 호출 실패로 인해 로컬 빈도 분석으로 대체되었습니다.",
    }

# --- [핵심] Gemini 분석 함수 ---
def analyze_comments(comments, _key=None):
    # 1. API 키 준비
    api_key = (_key or os.getenv("GEMINI_API_KEY", "")).strip()

    if not comments:
        return {"status": "error", "message": "코멘트 없음", "result": None}

    if not api_key:
        return {
            "status": "simulated",
            "message": "API Key 없음 (로컬 요약)",
            "result": _fallback_summary(comments),
        }

    # 2. 요청 데이터 구성
    prompt = PROMPT_TEMPLATE.format(comments="/n".join(comments))
    
    # [수정] generationConfig 추가 (JSON 응답 강제)
    payload_dict = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",  # JSON 모드 활성화
            "temperature": 0.1  # 분석의 일관성을 위해 낮춤
        }
    }
    payload = json.dumps(payload_dict).encode("utf-8")

    # [모델] 문서 기준 최신 모델 (2026년 현재 유효)
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key
    }

    print(f"--- [DEBUG] 요청 시작: {model_name} (JSON Mode) ---")

    # 3. API 호출 (Retry 로직)
    max_retries = 2
    response_data = None
    
    for attempt in range(max_retries + 1):
        try:
            req = request.Request(url, data=payload, headers=headers, method="POST")
            with request.urlopen(req, timeout=30) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                break 
        except error.HTTPError as e:
            error_msg = e.read().decode('utf-8')
            print(f"⚠️ HTTP Error {e.code}: {error_msg}")
            if e.code == 429:
                time.sleep(3)
                continue
            else:
                return {"status": "error", "message": f"HTTP {e.code}: {error_msg}", "result": None}
        except Exception as exc:
            return {"status": "error", "message": f"Connection Error: {exc}", "result": None}
    else:
        return {"status": "error", "message": "재시도 횟수 초과", "result": None}

    # 4. [수정] 응답 파싱 및 실제 데이터 추출
    try:
        candidates = response_data.get("candidates", [])
        if not candidates:
            return {"status": "error", "message": "Safety Filter에 의해 차단됨", "result": None}
        
        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        # JSON 모드로 요청했으므로, 텍스트를 JSON으로 파싱
        parsed_result = json.loads(raw_text)
        
        return {
            "status": "success",
            "message": "분석 완료",
            "result": {
                "sentiment": parsed_result.get("sentiment", "알 수 없음"),
                "keywords": parsed_result.get("keywords", []),
                "summary": parsed_result.get("summary", "")
            },
        }
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 원본 텍스트라도 반환
        return {
            "status": "partial_success",
            "message": "JSON 파싱 실패 (텍스트로 반환)",
            "result": {
                "sentiment": "-",
                "keywords": [],
                "summary": raw_text
            }
        }
