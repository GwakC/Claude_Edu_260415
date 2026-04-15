import json
import os

import requests as http_requests
from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage, SystemMessage

from services.storage_service import append_expense

UPSTAGE_OCR_URL = "https://api.upstage.ai/v1/document-digitization"

SYSTEM_PROMPT = """당신은 영수증 OCR 전문가입니다.
아래 영수증 텍스트를 분석하여 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

{
  "store_name": "가게명 (string, 필수)",
  "receipt_date": "날짜 YYYY-MM-DD (string, 필수)",
  "receipt_time": "시각 HH:MM (string, 없으면 null)",
  "category": "카테고리 (식료품|외식|교통|쇼핑|의료|기타 중 하나)",
  "items": [
    {
      "name": "품목명 (영수증 원문 그대로 유지. RB 1샷 등 샷 추가 항목은 별도 item 금지, 직전 메뉴 name 끝에 '+ 샷추가' 를 붙이고 금액 합산)",
      "quantity": 수량(int),
      "unit_price": 단가(int, 샷추가 금액 포함),
      "total_price": 소계(int)
    }
  ],
  "subtotal": 소계합계(int),
  "discount": 할인금액(int, 없으면 0),
  "tax": 세금(int, 없으면 0),
  "total_amount": 최종결제금액(int, 필수),
  "payment_method": "결제수단 (string, 없으면 null)"
}"""


def _ocr_extract_text(contents: bytes, content_type: str, filename: str) -> str:
    """Upstage Document OCR API로 이미지/PDF에서 텍스트 추출"""
    api_key = os.environ["UPSTAGE_API_KEY"]
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"document": (filename, contents, content_type)}
    data = {"model": "ocr"}

    response = http_requests.post(
        UPSTAGE_OCR_URL, headers=headers, files=files, data=data
    )
    response.raise_for_status()

    result = response.json()
    pages = result.get("pages", [])
    full_text = "\n".join(page.get("text", "") for page in pages)

    if not full_text.strip():
        raise ValueError("OCR 결과에서 텍스트를 추출할 수 없습니다.")

    return full_text.strip()


def _parse_with_llm(ocr_text: str) -> dict:
    """ChatUpstage (solar-pro)로 OCR 텍스트 → 구조화 JSON"""
    llm = ChatUpstage(
        api_key=os.environ["UPSTAGE_API_KEY"],
        model="solar-pro",
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"다음 영수증 텍스트를 JSON으로 추출해주세요:\n\n{ocr_text}"),
    ]

    response = llm.invoke(messages)
    raw_text = response.content.strip()

    # ```json ... ``` 마크다운 블록 제거
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    return json.loads(raw_text)


async def parse_receipt(contents: bytes, content_type: str, filename: str) -> dict:
    """
    영수증 파싱 파이프라인:
    1. Upstage OCR API → 텍스트 추출
    2. ChatUpstage LLM → 구조화 JSON
    3. expenses.json 저장
    """
    ocr_text = _ocr_extract_text(contents, content_type, filename)
    parsed = _parse_with_llm(ocr_text)

    expense = append_expense(
        {
            "raw_image_path": f"uploads/{filename}",
            **parsed,
        }
    )
    return expense
