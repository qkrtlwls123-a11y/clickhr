import json
import os
import time
from collections import Counter
from urllib import request, error

# --- [설정] 프롬프트 템플릿 ---
PROMPT_TEMPLATE = """
다음은 직원 교육 만족도 설문에 대한 정성 코멘트입니다.
핵심 감정(긍정/부정/중립) 분포와 핵심 키워드 5개를 한국어로 요약하세요.
코멘트 목록:
{comments}
""".strip()

# --- [보조] 로컬 분석 함수 (API 실패 시 작동) ---
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

# --- [핵심] Gemini 분석 함수 ---
def analyze_comments(comments, _key=None):
    # 1. API 키 가져오기 및 공백 제거
    api_key = (_key or os.getenv("GEMINI_API_KEY", "")).strip()

    # 2. 예외 처리: 코멘트가 없거나 키가 없는 경우
    if not comments:
        return {"status": "error", "message": "코멘트 없음", "result": None}

    if not api_key:
        return {
            "status": "simulated",
            "message": "API Key 없음 (로컬 요약)",
            "result": _fallback_summary(comments),
        }

    # 3. 요청 데이터(Payload) 만들기
    prompt = PROMPT_TEMPLATE.format(comments="\n".join(comments))
    
    # [중요] Gemini가 요구하는 정확한 JSON 구조
    payload_dict = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    payload = json.dumps(payload_dict).encode("utf-8")

    # 4. 모델 및 URL 설정 (가장 안정적인 1.5 Flash 사용)
    model_name = "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    # 5. 헤더 설정 (API 키는 헤더에 넣는 것이 가장 안전함)
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key
    }

    # 디버깅 로그 출력
    print(f"--- [DEBUG] 요청 시작 ---")
    print(f"Model: {model_name}")
    print(f"Key (앞5자리): {api_key[:5]}...") # 키 확인용
    print(f"Payload 크기: {len(payload)} bytes")
    print(f"-----------------------")

    # 6. 요청 전송 (Retry 로직 포함)
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            req = request.Request(url, data=payload, headers=headers, method="POST")
            
            with request.urlopen(req, timeout=30) as response:
                # 성공 시 결과 읽기
                response_body = response.read().decode("utf-8")
                response_data = json.loads(response_body)
                
                # 성공하면 바로 결과 처리로 이동
                break 

        except error.HTTPError as e:
            # [중요] 에러가 나면 구글이 보낸 상세 메시지를 읽음
            error_details = e.read().decode('utf-8')
            print(f"⚠️ HTTP Error {e.code}: {error_details}")

            if e.code == 429: # 너무 많은 요청
                print("⏳ 사용량 초과. 3초 대기 후 재시도...")
                time.sleep(3)
                continue
            elif e.code == 400: # Bad Request
                # 400은 재시도해도 안 됨. 바로 에러 리턴.
                return {
                    "status": "error",
                    "message": f"요청 형식 오류 (HTTP 400): {error_details}",
                    "result": None,
                }
            elif e.code == 403: # 권한 없음
                return {
                    "status": "error",
                    "message": "API 키 권한 없음 (HTTP 403). 새 키를 발급받으세요.",
                    "result": None,
                }
            else:
                return {
                    "status": "error",
                    "message": f"API 호출 에러 (HTTP {e.code})",
                    "result": None,
                }
                
        except Exception as exc:
            return {
                "status": "error",
                "message": f"연결 실패: {exc}",
                "result": None,
            }
    else:
        # for 문이 break 없이 끝난 경우 (모든 재시도 실패)
        return {
            "status": "error",
            "message": "재시도 횟수 초과",
            "result": None,
        }

    # 7. 응답 데이터 파싱
    candidates = response_data.get("candidates", [])
    if not candidates:
        # 안전 필터(Safety Filter)에 걸린 경우
        return {
            "status": "error",
            "message": "응답이 차단되었습니다 (Safety Filter).",
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
