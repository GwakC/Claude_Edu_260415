import base64
import io
import json
import os
import uuid
from datetime import datetime, timezone

from PIL import Image
from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage, SystemMessage

DATA_FILE = os.path.join(os.path.dirname(__file__), "../data/expenses.json")

SYSTEM_PROMPT = """당신은 영수증 OCR 전문가입니다.
영수증 이미지를 분석하여 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

{
  "store_name": "가게명 (string, 필수)",
  "receipt_date": "날짜 YYYY-MM-DD (string, 필수)",
  "receipt_time": "시각 HH:MM (string, 없으면 null)",
  "category": "카테고리 (식료품|외식|교통|쇼핑|의료|기타 중 하나)",
  "items": [
    {
      "name": "품목명",
      "quantity": 수량(int),
      "unit_price": 단가(int),
      "total_price": 소계(int)
    }
  ],
  "subtotal": 소계합계(int),
  "discount": 할인금액(int, 없으면 0),
  "tax": 세금(int, 없으면 0),
  "total_amount": 최종결제금액(int, 필수),
  "payment_method": "결제수단 (string, 없으면 null)"
}"""


def _to_base64_jpeg(contents: bytes, content_type: str) -> str:
    """이미지 또는 PDF 첫 페이지를 Base64 JPEG 문자열로 변환"""
    if content_type == "application/pdf":
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(contents, first_page=1, last_page=1, dpi=200)
        img = images[0]
    else:
        img = Image.open(io.BytesIO(contents)).convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _append_to_file(expense: dict) -> None:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.append(expense)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def parse_receipt(contents: bytes, content_type: str, filename: str) -> dict:
    """Upstage Vision LLM으로 영수증 파싱 후 expenses.json에 저장"""
    b64_image = _to_base64_jpeg(contents, content_type)

    llm = ChatUpstage(
        api_key=os.environ["UPSTAGE_API_KEY"],
        model="solar-pro",
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                },
                {"type": "text", "text": "이 영수증의 내용을 JSON으로 추출해주세요."},
            ]
        ),
    ]

    response = llm.invoke(messages)
    raw_text = response.content.strip()

    # ```json ... ``` 블록 처리
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    parsed = json.loads(raw_text)

    expense = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw_image_path": f"uploads/{filename}",
        **parsed,
    }

    _append_to_file(expense)
    return expense
