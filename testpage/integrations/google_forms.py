import json
import os
import uuid
from datetime import datetime
from urllib import request


def _build_choice_question_item(title, index):
    options = [
        {"value": "매우 그렇다"},
        {"value": "그렇다"},
        {"value": "보통"},
        {"value": "그렇지 않다"},
        {"value": "전혀 그렇지 않다"},
    ]

    return {
        "createItem": {
            "item": {
                "title": title,
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": options,
                            "shuffle": False,
                        },
                    }
                },
            },
            "location": {"index": index},
        }
    }


def create_google_form(title, questions, access_token=None):
    if access_token is None:
        access_token = os.getenv("GOOGLE_FORMS_ACCESS_TOKEN")

    if not questions:
        return {
            "status": "error",
            "message": "선택된 문항이 없습니다.",
            "form_id": None,
            "form_url": None,
        }

    if not access_token:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        simulated_id = f"SIM-{timestamp}-{uuid.uuid4().hex[:6]}"
        return {
            "status": "simulated",
            "message": "GOOGLE_FORMS_ACCESS_TOKEN이 없어 시뮬레이션 링크를 반환합니다.",
            "form_id": simulated_id,
            "form_url": f"https://forms.gle/{simulated_id}",
        }

    form_payload = json.dumps({"info": {"title": title}}).encode("utf-8")
    form_req = request.Request(
        "https://forms.googleapis.com/v1/forms",
        data=form_payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(form_req, timeout=15) as response:
            form_data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Google Forms API 호출 실패: {exc}",
            "form_id": None,
            "form_url": None,
        }

    form_id = form_data.get("formId")
    form_url = form_data.get("responderUri")

    requests = [
        _build_choice_question_item(question, index)
        for index, question in enumerate(questions)
    ]

    update_payload = json.dumps({"requests": requests}).encode("utf-8")
    update_req = request.Request(
        f"https://forms.googleapis.com/v1/forms/{form_id}:batchUpdate",
        data=update_payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(update_req, timeout=15):
            pass
    except Exception as exc:
        return {
            "status": "partial",
            "message": f"폼 생성은 완료되었으나 문항 추가 실패: {exc}",
            "form_id": form_id,
            "form_url": form_url,
        }

    return {
        "status": "success",
        "message": "Google Forms 설문이 생성되었습니다.",
        "form_id": form_id,
        "form_url": form_url,
    }
