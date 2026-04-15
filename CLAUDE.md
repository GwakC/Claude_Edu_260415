# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

영수증(JPG/PNG/PDF)을 업로드하면 **Upstage Vision LLM**이 자동으로 OCR·파싱하여 구조화된 지출 데이터로 변환하는 경량 웹 앱입니다. DB 없이 `expenses.json` 파일로 데이터를 관리합니다.

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 프론트엔드 | React 18 + Vite 5 + TailwindCSS 3 + Axios |
| 백엔드 | Python FastAPI + LangChain + Upstage Vision LLM |
| 데이터 저장 | `backend/data/expenses.json` (JSON 파일, DB 미사용) |
| 배포 | Vercel (프론트 정적 빌드 + 백엔드 서버리스) |
| OCR 모델 | `document-digitization-vision` (Upstage Document AI) |

---

## 프로젝트 구조

```
receipt-tracker/
├── frontend/               # React + Vite
│   ├── src/
│   │   ├── pages/          # Dashboard, UploadPage, ExpenseDetail
│   │   ├── components/     # Badge, Modal, Toast 등 공용 컴포넌트
│   │   └── api/            # Axios 인스턴스 및 API 호출 함수
│   ├── package.json
│   └── vite.config.js
├── backend/                # Python FastAPI
│   ├── main.py             # FastAPI 앱 진입점
│   ├── routers/            # 라우터별 엔드포인트 분리
│   ├── services/           # LangChain + Upstage OCR 로직
│   ├── data/
│   │   └── expenses.json   # 지출 데이터 누적 저장 파일
│   └── requirements.txt
├── vercel.json             # Vercel 빌드 및 라우팅 설정
└── .env                    # 로컬 환경변수 (커밋 금지)
```

---

## 개발 명령어

### 백엔드 (FastAPI)

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r backend/requirements.txt

# 개발 서버 실행 (포트 8000)
cd backend
uvicorn main:app --reload
```

### 프론트엔드 (React + Vite)

```bash
# 의존성 설치
cd frontend
npm install

# 개발 서버 실행 (포트 5173)
npm run dev

# 프로덕션 빌드
npm run build
```

---

## 환경변수

`.env` 파일에 아래 변수를 설정합니다 (Vercel 배포 시 Environment Variables에도 등록 필요):

| 변수명 | 설명 |
|--------|------|
| `UPSTAGE_API_KEY` | Upstage API 인증 키 |
| `VITE_API_BASE_URL` | 프론트에서 사용하는 백엔드 API 기본 URL |
| `DATA_FILE_PATH` | `expenses.json` 저장 경로 (기본값: `backend/data/expenses.json`) |

---

## API 엔드포인트

| 메서드 | URL | 설명 |
|--------|-----|------|
| `POST` | `/api/upload` | 영수증 업로드 및 OCR 파싱 (`multipart/form-data`) |
| `GET` | `/api/expenses` | 전체 지출 목록 조회 (`?from=&to=` 날짜 필터 지원) |
| `DELETE` | `/api/expenses/{id}` | 특정 지출 항목 삭제 |
| `PUT` | `/api/expenses/{id}` | 특정 지출 항목 수정 |
| `GET` | `/api/summary` | 지출 합계 통계 (`?month=` 필터 지원) |

---

## 핵심 데이터 흐름

```
영수증 파일 업로드
  → PIL/pdf2image로 이미지 전처리 + Base64 인코딩
  → LangChain Chain → ChatUpstage(Vision LLM) 호출
  → LangChain Output Parser로 구조화 JSON 추출
  → backend/data/expenses.json에 append 저장
  → 클라이언트에 파싱 결과 반환
```

---

## expenses.json 스키마

```json
{
  "id": "uuid-v4-string",
  "created_at": "2025-07-15T14:30:00Z",
  "store_name": "이마트 강남점",
  "receipt_date": "2025-07-15",
  "receipt_time": "13:25",
  "category": "식료품",
  "items": [
    { "name": "신라면 멀티팩", "quantity": 2, "unit_price": 4500, "total_price": 9000 }
  ],
  "subtotal": 10800,
  "discount": 500,
  "tax": 0,
  "total_amount": 10300,
  "payment_method": "신용카드",
  "raw_image_path": "uploads/receipt_20250715_001.jpg"
}
```

---

## 배포 (Vercel)

`vercel.json`에서 프론트 정적 빌드와 FastAPI 서버리스 함수를 함께 설정합니다:

```json
{
  "builds": [
    { "src": "frontend/package.json", "use": "@vercel/static-build" },
    { "src": "backend/main.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "backend/main.py" },
    { "src": "/(.*)", "dest": "frontend/dist/$1" }
  ]
}
```

> **주의**: Vercel 서버리스 환경은 컨테이너 재시작 시 파일 시스템이 초기화됩니다. `expenses.json` 영속성이 필요한 경우 Vercel KV(Redis) 또는 Railway/Render 배포로 전환하세요.

---

## 지원 파일 형식 및 제약

- 영수증 파일: JPG, PNG, PDF (최대 10MB)
- 한국어·영어 영수증만 지원 (파싱 성공률 목표 80% 이상)
- 단일 사용자 기준 설계 (동시 접속 다중 사용자 미지원)
- 로그인/인증 미구현 (1차 범위 제외)
