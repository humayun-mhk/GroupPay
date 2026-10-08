from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.expense import Expense, ExpenseParticipant, SplitType
from app.models.group import Group
from app.models.group_member import GroupMember, GroupRole
from app.models.settlement import Notification, SettlementStatus
from app.models.user import User
from app.schemas.settlement import SettlementCreate
from app.services.balances import calculate_group_balances, simplify_debts
from app.services.notifications import list_notifications, mark_all_read, mark_read, unread_count
from app.services.settlements import cancel, claim_paid, confirm, create_request, reject
from tests.conftest import auth, register


@pytest.fixture
def finance_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        alice = User(full_name="Alice", email="alice@test.local", password_hash="x")
        bob = User(full_name="Bob", email="bob@test.local", password_hash="x")
        db.add_all([alice, bob])
        db.flush()
        group = Group(name="Dinner Friends", created_by=alice.id)
        db.add(group)
        db.flush()
        db.add_all([GroupMember(group_id=group.id, user_id=alice.id, role=GroupRole.ADMIN), GroupMember(group_id=group.id, user_id=bob.id, role=GroupRole.MEMBER)])
        expense = Expense(group_id=group.id, title="Dinner", total_amount=Decimal("200.00"), currency="PKR", paid_by_user_id=alice.id, split_type=SplitType.EQUAL, expense_date=__import__("datetime").datetime.now(__import__("datetime").timezone.utc), created_by=alice.id)
        db.add(expense)
        db.flush()
        db.add_all([ExpenseParticipant(expense_id=expense.id, user_id=alice.id, amount_owed=Decimal("100.00")), ExpenseParticipant(expense_id=expense.id, user_id=bob.id, amount_owed=Decimal("100.00"))])
        db.commit()
        yield db, alice, bob, group
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_confirmation_updates_balances_and_notifies_parties(finance_db):
    db, alice, bob, group = finance_db
    request = create_request(db, group.id, alice, SettlementCreate(payer_id=bob.id, amount=Decimal("60.00"), note="Dinner"))
    assert request.status == SettlementStatus.PENDING
    assert unread_count(db, bob.id) == 1
    with pytest.raises(HTTPException) as denied:
        claim_paid(db, request.id, alice)
    assert denied.value.status_code == 403
    claim_paid(db, request.id, bob)
    assert request.status == SettlementStatus.PAYMENT_CLAIMED
    assert calculate_group_balances(db, group.id)[bob.id] == Decimal("-100.00")
    with pytest.raises(HTTPException) as wrong_receiver:
        confirm(db, request.id, bob)
    assert wrong_receiver.value.status_code == 403
    confirm(db, request.id, alice)
    assert request.status == SettlementStatus.CONFIRMED
    assert calculate_group_balances(db, group.id) == {alice.id: Decimal("40.00"), bob.id: Decimal("-40.00")}
    with pytest.raises(HTTPException) as twice:
        confirm(db, request.id, alice)
    assert twice.value.status_code == 409
    assert len(request.events) == 3
    assert unread_count(db, bob.id) == 2


def test_partial_multiple_requests_and_limit(finance_db):
    db, alice, bob, group = finance_db
    first = create_request(db, group.id, alice, SettlementCreate(payer_id=bob.id, amount=Decimal("40.00")))
    second = create_request(db, group.id, alice, SettlementCreate(payer_id=bob.id, amount=Decimal("60.00")))
    assert first.status == second.status == SettlementStatus.PENDING
    with pytest.raises(HTTPException) as over:
        create_request(db, group.id, alice, SettlementCreate(payer_id=bob.id, amount=Decimal("0.01")))
    assert over.value.status_code == 409
    claim_paid(db, first.id, bob)
    reject(db, first.id, alice, "Not received yet")
    assert calculate_group_balances(db, group.id)[bob.id] == Decimal("-100.00")
    assert len(simplify_debts(calculate_group_balances(db, group.id))) == 1
    # Rejected requests release their reserved amount for a fresh request.
    third = create_request(db, group.id, alice, SettlementCreate(payer_id=bob.id, amount=Decimal("40.00")))
    assert third.status == SettlementStatus.PENDING


def test_self_member_and_cancel_validation(finance_db):
    db, alice, bob, group = finance_db
    with pytest.raises(HTTPException) as self_request:
        create_request(db, group.id, alice, SettlementCreate(payer_id=alice.id, amount=Decimal("1.00")))
    assert self_request.value.status_code == 400
    request = create_request(db, group.id, alice, SettlementCreate(payer_id=bob.id, amount=Decimal("20.00")))
    cancel(db, request.id, alice)
    assert request.status == SettlementStatus.CANCELLED
    with pytest.raises(HTTPException) as invalid:
        claim_paid(db, request.id, bob)
    assert invalid.value.status_code == 409
    with pytest.raises(ValidationError):
        SettlementCreate(payer_id=bob.id, amount=Decimal("0.00"))


def test_new_expense_after_confirmation_recalculates_net_balances(finance_db):
    db, alice, bob, group = finance_db
    request = create_request(db, group.id, alice, SettlementCreate(payer_id=bob.id, amount=Decimal("100.00")))
    claim_paid(db, request.id, bob)
    confirm(db, request.id, alice)
    next_expense = Expense(group_id=group.id, title="Coffee", total_amount=Decimal("30.00"), currency="PKR", paid_by_user_id=bob.id, split_type=SplitType.EQUAL, expense_date=__import__("datetime").datetime.now(__import__("datetime").timezone.utc), created_by=bob.id)
    db.add(next_expense)
    db.flush()
    db.add_all([ExpenseParticipant(expense_id=next_expense.id, user_id=alice.id, amount_owed=Decimal("15.00")), ExpenseParticipant(expense_id=next_expense.id, user_id=bob.id, amount_owed=Decimal("15.00"))])
    db.commit()
    assert calculate_group_balances(db, group.id) == {alice.id: Decimal("-15.00"), bob.id: Decimal("15.00")}


def test_notification_ownership_and_read(finance_db):
    db, alice, bob, group = finance_db
    create_request(db, group.id, alice, SettlementCreate(payer_id=bob.id, amount=Decimal("25.00")))
    own = list_notifications(db, bob.id)
    assert len(own) == 1 and own[0].type == "PAYMENT_REQUEST"
    assert list_notifications(db, alice.id) == []
    mark_read(db, bob.id, own[0].id)
    assert unread_count(db, bob.id) == 0
    db.add(Notification(user_id=bob.id, type="PAYMENT_REQUEST", title="Another", message="Test"))
    db.commit()
    assert mark_all_read(db, bob.id) == 1
    assert unread_count(db, bob.id) == 0


def test_settlement_api_serialization_and_full_lifecycle(client):
    alice = register(client, "Alice", "alice-api@example.com")
    bob = register(client, "Bob", "bob-api@example.com")
    ah, bh = auth(alice["access_token"]), auth(bob["access_token"])
    bob_id = client.get("/api/v1/auth/me", headers=bh).json()["id"]
    friend = client.post(f"/api/v1/friends/requests/{bob_id}", headers=ah)
    assert friend.status_code == 201
    assert client.post(f"/api/v1/friends/requests/{friend.json()['id']}/accept", headers=bh).status_code == 200
    group = client.post("/api/v1/groups", headers=ah, json={"name": "Dinner Friends"}).json()
    assert client.post(f"/api/v1/groups/{group['id']}/members", headers=ah, json={"user_id": bob_id}).status_code == 201
    expense = client.post(f"/api/v1/groups/{group['id']}/expenses", headers=ah, json={"title": "Dinner", "total_amount": "100.00", "paid_by_user_id": alice["user"]["id"], "split_type": "EQUAL", "expense_date": "2026-10-01T18:00:00Z", "participants": [{"user_id": alice["user"]["id"]}, {"user_id": bob_id} ]})
    assert expense.status_code == 201, expense.text
    created = client.post(f"/api/v1/groups/{group['id']}/settlement-requests", headers=ah, json={"payer_id": bob_id, "amount": "25.00", "note": "Dinner"})
    assert created.status_code == 201, created.text
    assert created.json()["group_name"] == "Dinner Friends"
    request_id = created.json()["id"]
    assert client.get("/api/v1/settlement-requests/incoming", headers=bh).json()[0]["id"] == request_id
    assert client.post(f"/api/v1/settlement-requests/{request_id}/claim-paid", headers=bh).status_code == 200
    assert client.post(f"/api/v1/settlement-requests/{request_id}/confirm", headers=ah).status_code == 200
    balance = client.get(f"/api/v1/groups/{group['id']}/balances", headers=ah).json()
    assert next(row["net_balance"] for row in balance if row["user"]["id"] == bob_id) == "-25.00"
    assert client.post(f"/api/v1/settlement-requests/{request_id}/confirm", headers=ah).status_code == 409
    assert client.get("/api/v1/notifications", headers=bh).status_code == 200
