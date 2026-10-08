from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.settlement import SettlementEvent, SettlementRequest, SettlementStatus
from app.models.user import User
from app.payments import ManualPaymentProvider
from app.schemas.settlement import SettlementCreate
from app.services.balances import calculate_group_balances, simplify_debts
from app.services.expense_calculator import ZERO, money
from app.services.groups import require_member
from app.services.notifications import notify

manual_provider = ManualPaymentProvider()


def _load(db: Session, settlement_id: int, lock: bool = False) -> SettlementRequest:
    stmt = select(SettlementRequest).options(joinedload(SettlementRequest.requester), joinedload(SettlementRequest.payer), joinedload(SettlementRequest.group), selectinload(SettlementRequest.events)).where(SettlementRequest.id == settlement_id)
    if lock:
        stmt = stmt.with_for_update()
    request = db.execute(stmt).unique().scalar_one_or_none()
    if request is None:
        raise HTTPException(status_code=404, detail="Settlement request not found")
    return request


def create_request(db: Session, group_id: int, requester: User, data: SettlementCreate) -> SettlementRequest:
    require_member(db, group_id, requester.id)
    group = db.scalar(select(Group).where(Group.id == group_id).with_for_update())
    payer = db.get(User, data.payer_id)
    if payer is None or not payer.is_active or not db.scalar(select(GroupMember.id).where(GroupMember.group_id == group_id, GroupMember.user_id == payer.id)):
        raise HTTPException(status_code=400, detail="Payer must be an active member of this group")
    if requester.id == payer.id:
        raise HTTPException(status_code=400, detail="You cannot request payment from yourself")
    amount = money(data.amount)
    if amount != data.amount:
        raise HTTPException(status_code=422, detail="Amount can have at most two decimal places")
    obligations = simplify_debts(calculate_group_balances(db, group_id))
    pair_amount = next((value for debtor, creditor, value in obligations if debtor == payer.id and creditor == requester.id), ZERO)
    # Sum every open request for this pair to reserve the outstanding amount.
    from sqlalchemy import func
    reserved = db.scalar(select(func.coalesce(func.sum(SettlementRequest.amount), 0)).where(SettlementRequest.group_id == group_id, SettlementRequest.payer_id == payer.id, SettlementRequest.requester_id == requester.id, SettlementRequest.status.in_([SettlementStatus.PENDING, SettlementStatus.PAYMENT_CLAIMED]))) or ZERO
    if amount > pair_amount - reserved:
        raise HTTPException(status_code=409, detail="Amount exceeds the unrequested outstanding obligation")
    request = SettlementRequest(group_id=group_id, requester_id=requester.id, payer_id=payer.id, amount=amount, note=data.note.strip() if data.note else None, source_type="MANUAL")
    db.add(request)
    db.flush()
    db.add(SettlementEvent(settlement_request_id=request.id, actor_id=requester.id, action="PENDING", note=request.note))
    payment = manual_provider.create_payment(amount, "PKR", f"settlement-{request.id}")
    notify(db, payer.id, "PAYMENT_REQUEST", "Payment requested", f"{requester.full_name} requested Rs. {amount} in {group.name}. {payment.instructions}", "settlement", request.id)
    db.commit()
    db.expire_all()
    return _load(db, request.id)


def _transition(db: Session, request_id: int, actor: User, from_status: SettlementStatus, to_status: SettlementStatus, actor_id: int, note: str | None = None):
    request = _load(db, request_id, lock=True)
    if actor.id != actor_id:
        raise HTTPException(status_code=403, detail="You are not allowed to perform this action")
    expected_actor = request.payer_id if to_status == SettlementStatus.PAYMENT_CLAIMED else request.requester_id
    if to_status == SettlementStatus.CANCELLED:
        expected_actor = request.requester_id
    if actor.id != expected_actor:
        raise HTTPException(status_code=403, detail="You are not allowed to perform this action")
    now = datetime.now(timezone.utc)
    if to_status == SettlementStatus.CANCELLED:
        manual_provider.cancel_payment(f"settlement-{request.id}")
    values = {"status": to_status, "updated_at": now}
    if to_status == SettlementStatus.PAYMENT_CLAIMED:
        values["claimed_paid_at"] = now
    elif to_status == SettlementStatus.CONFIRMED:
        values["confirmed_at"] = now
    elif to_status == SettlementStatus.REJECTED:
        values["rejected_at"] = now
    result = db.execute(update(SettlementRequest).where(SettlementRequest.id == request_id, SettlementRequest.status == from_status).values(**values).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Cannot change settlement from {request.status.value}")
    db.add(SettlementEvent(settlement_request_id=request_id, actor_id=actor.id, action=to_status.value, note=note))
    if to_status == SettlementStatus.PAYMENT_CLAIMED:
        notify(db, request.requester_id, "PAYMENT_CLAIMED", "Payment marked as paid", f"{request.payer.full_name} says they paid Rs. {request.amount}.", "settlement", request.id)
    elif to_status == SettlementStatus.CONFIRMED:
        notify(db, request.payer_id, "PAYMENT_CONFIRMED", "Payment confirmed", f"{request.requester.full_name} confirmed Rs. {request.amount}.", "settlement", request.id)
    elif to_status == SettlementStatus.REJECTED:
        notify(db, request.payer_id, "PAYMENT_REJECTED", "Payment claim rejected", f"{request.requester.full_name} rejected the payment claim. The balance remains outstanding.", "settlement", request.id)
    elif to_status == SettlementStatus.CANCELLED:
        notify(db, request.payer_id, "PAYMENT_CANCELLED", "Payment request cancelled", f"{request.requester.full_name} cancelled the request.", "settlement", request.id)
    db.commit()
    db.expire_all()
    return _load(db, request_id)


def claim_paid(db: Session, request_id: int, actor: User):
    return _transition(db, request_id, actor, SettlementStatus.PENDING, SettlementStatus.PAYMENT_CLAIMED, actor.id)


def confirm(db: Session, request_id: int, actor: User):
    return _transition(db, request_id, actor, SettlementStatus.PAYMENT_CLAIMED, SettlementStatus.CONFIRMED, actor.id)


def reject(db: Session, request_id: int, actor: User, note: str | None = None):
    return _transition(db, request_id, actor, SettlementStatus.PAYMENT_CLAIMED, SettlementStatus.REJECTED, actor.id, note)


def cancel(db: Session, request_id: int, actor: User):
    return _transition(db, request_id, actor, SettlementStatus.PENDING, SettlementStatus.CANCELLED, actor.id)


def get_request(db: Session, request_id: int, actor: User):
    request = _load(db, request_id)
    if actor.id not in (request.requester_id, request.payer_id):
        raise HTTPException(status_code=404, detail="Settlement request not found")
    return request


def list_requests(db: Session, actor: User, incoming: bool):
    column = SettlementRequest.payer_id if incoming else SettlementRequest.requester_id
    return db.scalars(select(SettlementRequest).options(joinedload(SettlementRequest.group), joinedload(SettlementRequest.requester), joinedload(SettlementRequest.payer), selectinload(SettlementRequest.events)).where(column == actor.id).order_by(SettlementRequest.created_at.desc())).unique().all()


def group_history(db: Session, group_id: int, actor: User):
    require_member(db, group_id, actor.id)
    return db.scalars(select(SettlementRequest).options(joinedload(SettlementRequest.group), joinedload(SettlementRequest.requester), joinedload(SettlementRequest.payer), selectinload(SettlementRequest.events)).where(SettlementRequest.group_id == group_id).order_by(SettlementRequest.created_at.desc())).unique().all()
