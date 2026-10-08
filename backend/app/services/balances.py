from collections.abc import Mapping
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.expense import Expense, ExpenseParticipant
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.settlement import SettlementRequest, SettlementStatus
from app.models.user import User
from app.services.expense_calculator import CENT, ZERO, money


def calculate_group_balances(db: Session, group_id: int) -> dict[int, Decimal]:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    balances = {
        user_id: ZERO
        for user_id in db.scalars(
            select(GroupMember.user_id).where(GroupMember.group_id == group_id)
        )
    }
    expenses = db.scalars(
        select(Expense)
        .options(selectinload(Expense.participants))
        .where(Expense.group_id == group_id)
    ).all()
    for expense in expenses:
        balances[expense.paid_by_user_id] = (
            balances.get(expense.paid_by_user_id, ZERO) + expense.total_amount
        )
        for participant in expense.participants:
            balances[participant.user_id] = (
                balances.get(participant.user_id, ZERO) - participant.amount_owed
            )
    confirmed = db.scalars(
        select(SettlementRequest).where(
            SettlementRequest.group_id == group_id,
            SettlementRequest.status == SettlementStatus.CONFIRMED,
        )
    ).all()
    for settlement in confirmed:
        # A confirmed transfer reduces the payer's debt and the receiver's credit.
        balances[settlement.payer_id] = balances.get(settlement.payer_id, ZERO) + settlement.amount
        balances[settlement.requester_id] = balances.get(settlement.requester_id, ZERO) - settlement.amount
    return {user_id: money(amount) for user_id, amount in balances.items()}


def simplify_debts(balances: Mapping[int, Decimal]) -> list[tuple[int, int, Decimal]]:
    """Greedily match sorted debtors to creditors; output is deterministic and cent exact."""
    normalized = {user_id: money(value) for user_id, value in balances.items()}
    total = sum(normalized.values(), ZERO)
    if total != ZERO:
        raise ValueError(f"Group balances must net to zero; found residual {total}")
    debtors = [
        [user_id, -amount] for user_id, amount in sorted(normalized.items()) if amount < ZERO
    ]
    creditors = [
        [user_id, amount] for user_id, amount in sorted(normalized.items()) if amount > ZERO
    ]
    settlements: list[tuple[int, int, Decimal]] = []
    debtor_index = creditor_index = 0
    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor_id, debt = debtors[debtor_index]
        creditor_id, credit = creditors[creditor_index]
        transfer = min(debt, credit).quantize(CENT)
        if transfer <= ZERO:
            break
        settlements.append((debtor_id, creditor_id, transfer))
        debtors[debtor_index][1] = debt - transfer
        creditors[creditor_index][1] = credit - transfer
        if debtors[debtor_index][1] == ZERO:
            debtor_index += 1
        if creditors[creditor_index][1] == ZERO:
            creditor_index += 1
    if debtor_index != len(debtors) or creditor_index != len(creditors):
        raise ValueError("Could not settle group balances exactly")
    return settlements


def group_users(db: Session, group_id: int) -> dict[int, User]:
    current_members = select(GroupMember.user_id.label("user_id")).where(
        GroupMember.group_id == group_id
    )
    historical_payers = select(Expense.paid_by_user_id.label("user_id")).where(
        Expense.group_id == group_id
    )
    historical_participants = (
        select(ExpenseParticipant.user_id.label("user_id"))
        .join(Expense, Expense.id == ExpenseParticipant.expense_id)
        .where(Expense.group_id == group_id)
    )
    user_ids = set(db.scalars(current_members.union(historical_payers, historical_participants)))
    users = db.scalars(select(User).where(User.id.in_(user_ids))).all() if user_ids else []
    return {user.id: user for user in users}
