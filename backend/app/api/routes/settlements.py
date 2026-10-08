from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.settlement import SettlementCreate, SettlementResponse
from app.services.settlements import (
    cancel,
    claim_paid,
    confirm,
    create_request,
    get_request,
    group_history,
    list_requests,
    reject,
)

router = APIRouter(tags=["manual settlements"])


@router.post("/groups/{group_id}/settlement-requests", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
def create(group_id: int, data: SettlementCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return create_request(db, group_id, current, data)


@router.get("/settlement-requests/incoming", response_model=list[SettlementResponse])
def incoming(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return list_requests(db, current, incoming=True)


@router.get("/settlement-requests/outgoing", response_model=list[SettlementResponse])
def outgoing(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return list_requests(db, current, incoming=False)


@router.get("/settlement-requests/{request_id}", response_model=SettlementResponse)
def detail(request_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return get_request(db, request_id, current)


@router.post("/settlement-requests/{request_id}/claim-paid", response_model=SettlementResponse)
def mark_paid(request_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return claim_paid(db, request_id, current)


@router.post("/settlement-requests/{request_id}/confirm", response_model=SettlementResponse)
def confirm_payment(request_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return confirm(db, request_id, current)


@router.post("/settlement-requests/{request_id}/reject", response_model=SettlementResponse)
def reject_payment(request_id: int, note: str | None = None, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return reject(db, request_id, current, note)


@router.post("/settlement-requests/{request_id}/cancel", response_model=SettlementResponse)
def cancel_request(request_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return cancel(db, request_id, current)


@router.get("/groups/{group_id}/settlement-history", response_model=list[SettlementResponse])
def history(group_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return group_history(db, group_id, current)
