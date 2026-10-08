from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import Message
from app.schemas.expense import (
    BalanceLine,
    ExpenseCreate,
    ExpensePage,
    ExpensePreviewResponse,
    ExpenseResponse,
    ExpenseUpdate,
    GroupSummary,
    SettlementSuggestion,
)
from app.services.expenses import (
    balances_with_users,
    create_expense,
    delete_expense,
    get_authorized_expense,
    group_summary,
    list_expenses,
    preview_expense,
    settlements_with_users,
    update_expense,
)

router = APIRouter(tags=["expenses and balances"])


@router.post("/groups/{group_id}/expenses/preview", response_model=ExpensePreviewResponse)
def preview(
    group_id: int,
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    allocations = preview_expense(db, group_id, current, data)
    return {
        "total_amount": data.total_amount,
        "currency": data.currency,
        "split_type": data.split_type,
        "allocations": allocations,
    }


@router.post(
    "/groups/{group_id}/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(
    group_id: int,
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return create_expense(db, group_id, current, data)


@router.get("/groups/{group_id}/expenses", response_model=ExpensePage)
def history(
    group_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    items, total = list_expenses(db, group_id, current, offset, limit)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/groups/{group_id}/balances", response_model=list[BalanceLine])
def balances(
    group_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    return balances_with_users(db, group_id, current)


@router.get("/groups/{group_id}/settlements", response_model=list[SettlementSuggestion])
def settlements(
    group_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    return settlements_with_users(db, group_id, current)


@router.get("/groups/{group_id}/summary", response_model=GroupSummary)
def summary(
    group_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    return group_summary(db, group_id, current)


@router.get("/expenses/{expense_id}", response_model=ExpenseResponse)
def detail(
    expense_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    return get_authorized_expense(db, expense_id, current)


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse)
def update(
    expense_id: int,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return update_expense(db, expense_id, current, data)


@router.delete("/expenses/{expense_id}", response_model=Message)
def delete(
    expense_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    delete_expense(db, expense_id, current)
    return {"message": "Expense deleted"}
