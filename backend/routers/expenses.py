import json
import os
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

DATA_FILE = os.path.join(os.path.dirname(__file__), "../data/expenses.json")

router = APIRouter()


def _load() -> list:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: list) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class ExpenseUpdate(BaseModel):
    store_name: Optional[str] = None
    receipt_date: Optional[str] = None
    receipt_time: Optional[str] = None
    category: Optional[str] = None
    items: Optional[list] = None
    subtotal: Optional[int] = None
    discount: Optional[int] = None
    tax: Optional[int] = None
    total_amount: Optional[int] = None
    payment_method: Optional[str] = None


@router.get("/expenses")
def get_expenses(from_: Optional[str] = None, to: Optional[str] = None):
    """전체 지출 내역 조회 (날짜 필터 선택)"""
    expenses = _load()

    if from_:
        expenses = [e for e in expenses if e.get("receipt_date", "") >= from_]
    if to:
        expenses = [e for e in expenses if e.get("receipt_date", "") <= to]

    return expenses


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: str):
    """특정 지출 항목 삭제"""
    expenses = _load()
    filtered = [e for e in expenses if e["id"] != expense_id]

    if len(filtered) == len(expenses):
        raise HTTPException(status_code=404, detail="해당 항목을 찾을 수 없습니다.")

    _save(filtered)
    return {"message": "삭제되었습니다.", "id": expense_id}


@router.put("/expenses/{expense_id}")
def update_expense(expense_id: str, body: ExpenseUpdate):
    """특정 지출 항목 수정"""
    expenses = _load()
    idx = next((i for i, e in enumerate(expenses) if e["id"] == expense_id), None)

    if idx is None:
        raise HTTPException(status_code=404, detail="해당 항목을 찾을 수 없습니다.")

    update_data = body.model_dump(exclude_none=True)
    expenses[idx].update(update_data)
    _save(expenses)
    return expenses[idx]


@router.get("/summary")
def get_summary(month: Optional[str] = None):
    """지출 합계 통계 조회 (month: YYYY-MM 형식)"""
    expenses = _load()

    if month:
        expenses = [e for e in expenses if e.get("receipt_date", "").startswith(month)]

    total = sum(e.get("total_amount", 0) for e in expenses)

    current_month = date.today().strftime("%Y-%m")
    all_expenses = _load()
    month_expenses = [
        e for e in all_expenses if e.get("receipt_date", "").startswith(current_month)
    ]
    month_total = sum(e.get("total_amount", 0) for e in month_expenses)

    category_summary: dict[str, int] = {}
    for e in expenses:
        cat = e.get("category", "기타")
        category_summary[cat] = category_summary.get(cat, 0) + e.get("total_amount", 0)

    return {
        "total_amount": total,
        "month_total": month_total,
        "category_summary": category_summary,
        "count": len(expenses),
    }
