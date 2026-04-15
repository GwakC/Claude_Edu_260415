from fastapi import APIRouter, UploadFile, File, HTTPException
from services.ocr_service import parse_receipt

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

router = APIRouter()


@router.post("/upload")
async def upload_receipt(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. JPG, PNG, PDF만 허용됩니다. (받은 형식: {file.content_type})",
        )

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 크기는 10MB를 초과할 수 없습니다.")

    try:
        result = await parse_receipt(contents, file.content_type, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 파싱 실패: {str(e)}")

    return result
