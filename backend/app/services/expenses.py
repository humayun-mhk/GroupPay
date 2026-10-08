from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.expense import Expense, ExpenseParticipant, SplitType
from app.models.group_member import GroupMember, GroupRole
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, SplitParticipantInput
from app.services.balances import calculate_group_balances, group_users, simplify_debts
from app.services.expense_calculator import (
    ZERO,
    SplitInput,
    SplitValidationError,
    calculate_split,
    money,
)
from app.services.groups import require_member
from app.services.notifications import notify


def _get_expense(db: Session, expense_id: int) -> Expense:
    expense = db.scalar(
        select(Expense)
        .options(
            selectinload(Expense.participants).selectinload(ExpenseParticipant.user),
            selectinload(Expense.payer),
        )
        .where(Expense.id == expense_id)
    )
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


def get_authorized_expense(db: Session, expense_id: int, current: User) -> Expense:
    expense = _get_expense(db, expense_id)
    require_member(db, expense.group_id, current.id)
    return expense


def _authorize_editor(db: Session, expense: Expense, current: User) -> None:
    member = require_member(db, expense.group_id, current.id)
    if expense.created_by != current.id and member.role != GroupRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only the expense creator or a group admin can change this expense",
        )


def _split_inputs(entries: list[SplitParticipantInput]) -> list[SplitInput]:
    return [
        SplitInput(user_id=e.user_id, amount=e.amount, percentage=e.percentage, shares=e.shares)
        for e in entries
    ]


def _validate_members(
    db: Session, group_id: int, payer_id: int, participants: list[SplitParticipantInput]
) -> None:
    member_ids = set(
        db.scalars(select(GroupMember.user_id).where(GroupMember.group_id == group_id))
    )
    if payer_id not in member_ids:
        raise HTTPException(status_code=422, detail="The payer must be a member of this group")
    if not participants:
        raise HTTPException(status_code=422, detail="At least one participant is required")
    if any(participant.user_id not in member_ids for participant in participants):
        raise HTTPException(
            status_code=422, detail="Every participant must be a member of this group"
        )


def preview_expense(db: Session, group_id: int, current: User, data: ExpenseCreate) -> list:
    require_member(db, group_id, current.id)
    _validate_members(db, group_id, data.paid_by_user_id, data.participants)
    try:
        return calculate_split(data.total_amount, data.split_type, _split_inputs(data.participants))
    except SplitValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def create_expense(db: Session, group_id: int, current: User, data: ExpenseCreate) -> Expense:
    require_member(db, group_id, current.id)
    _validate_members(db, group_id, data.paid_by_user_id, data.participants)
    try:
        allocations = calculate_split(
            data.total_amount, data.split_type, _split_inputs(data.participants)
        )
    except SplitValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    expense = Expense(
        group_id=group_id,
        title=data.title,
        description=data.description,
        total_amount=money(data.total_amount),
        currency=data.currency,
        paid_by_user_id=data.paid_by_user_id,
        split_type=data.split_type,
        expense_date=data.expense_date,
        created_by=current.id,
    )
    db.add(expense)
    db.flush()
    db.add_all(
        [
            ExpenseParticipant(
                expense_id=expense.id,
                user_id=a.user_id,
                amount_owed=a.amount_owed,
                percentage=a.percentage,
                shares=a.shares,
            )
            for a in allocations
        ]
    )
    member_ids = db.scalars(select(GroupMember.user_id).where(GroupMember.group_id == group_id, GroupMember.user_id != current.id)).all()
    for user_id in member_ids:
        notify(db, user_id, "EXPENSE_ADDED", "New group expense", f'{current.full_name} added "{data.title}" — Rs. {money(data.total_amount)}.', "expense", expense.id)
    db.commit()
    return _get_expense(db, expense.id)


def list_expenses(
    db: Session, group_id: int, current: User, offset: int = 0, limit: int = 20
) -> tuple[list[Expense], int]:
    require_member(db, group_id, current.id)
    total = db.scalar(select(func.count(Expense.id)).where(Expense.group_id == group_id)) or 0
    items = db.scalars(
        select(Expense)
        .options(
            selectinload(Expense.participants).selectinload(ExpenseParticipant.user),
            selectinload(Expense.payer),
        )
        .where(Expense.group_id == group_id)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return items, total


def update_expense(db: Session, expense_id: int, current: User, data: ExpenseUpdate) -> Expense:
    expense = _get_expense(db, expense_id)
    _authorize_editor(db, expense, current)
    changes = data.model_dump(exclude_unset=True)
    for field in (
        "total_amount",
        "currency",
        "paid_by_user_id",
        "split_type",
        "expense_date",
        "participants",
    ):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
    next_amount = changes.get("total_amount", expense.total_amount)
    next_split_type = changes.get("split_type", expense.split_type)
    next_payer = changes.get("paid_by_user_id", expense.paid_by_user_id)
    if "participants" in changes:
        inputs = [SplitParticipantInput.model_validate(item) for item in changes["participants"]]
    else:
        inputs = [
            SplitParticipantInput(
                user_id=p.user_id,
                amount=p.amount_owed if next_split_type == SplitType.EXACT else None,
                percentage=p.percentage if next_split_type == SplitType.PERCENTAGE else None,
                shares=p.shares if next_split_type == SplitType.SHARES else None,
            )
            for p in expense.participants
        ]
    _validate_members(db, expense.group_id, next_payer, inputs)
    try:
        allocations = calculate_split(next_amount, next_split_type, _split_inputs(inputs))
    except SplitValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    for key, value in changes.items():
        if key != "participants":
            setattr(expense, key, money(value) if key == "total_amount" else value)
    expense.participants.clear()
    db.flush()
    expense.participants.extend(
        [
            ExpenseParticipant(
                user_id=a.user_id,
                amount_owed=a.amount_owed,
                percentage=a.percentage,
                shares=a.shares,
            )
            for a in allocations
        ]
    )
    db.commit()
    return _get_expense(db, expense.id)


def delete_expense(db: Session, expense_id: int, current: User) -> None:
    expense = _get_expense(db, expense_id)
    _authorize_editor(db, expense, current)
    db.delete(expense)
    db.commit()


def balances_with_users(db: Session, group_id: int, current: User) -> list[dict]:
    require_member(db, group_id, current.id)
    balances = calculate_group_balances(db, group_id)
    users = group_users(db, group_id)
    return [
        {
            "user": users[user_id],
            "net_balance": balance,
            "amount_owed": max(-balance, ZERO),
            "amount_owed_to_user": max(balance, ZERO),
        }
        for user_id, balance in sorted(balances.items())
    ]


def settlements_with_users(db: Session, group_id: int, current: User) -> list[dict]:
    require_member(db, group_id, current.id)
    balances = calculate_group_balances(db, group_id)
    users = group_users(db, group_id)
    suggestions = simplify_debts(balances)
    return [
        {
            "from_user": users[debtor],
            "to_user": users[creditor],
            "amount": amount,
            "currency": "PKR",
        }
        for debtor, creditor, amount in suggestions
    ]


def group_summary(db: Session, group_id: int, current: User) -> dict:
    require_member(db, group_id, current.id)
    balances = calculate_group_balances(db, group_id)
    total_spending = db.scalar(
        select(func.coalesce(func.sum(Expense.total_amount), 0)).where(Expense.group_id == group_id)
    ) or Decimal("0.00")
    total_paid = db.scalar(
        select(func.coalesce(func.sum(Expense.total_amount), 0)).where(
            Expense.group_id == group_id, Expense.paid_by_user_id == current.id
        )
    ) or Decimal("0.00")
    total_share = db.scalar(
        select(func.coalesce(func.sum(ExpenseParticipant.amount_owed), 0))
        .join(Expense, Expense.id == ExpenseParticipant.expense_id)
        .where(Expense.group_id == group_id, ExpenseParticipant.user_id == current.id)
    ) or Decimal("0.00")
    recent = db.scalars(
        select(Expense)
        .options(
            selectinload(Expense.participants).selectinload(ExpenseParticipant.user),
            selectinload(Expense.payer),
        )
        .where(Expense.group_id == group_id)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(5)
    ).all()
    balance = balances.get(current.id, ZERO)
    suggestions = simplify_debts(balances)
    return {
        "group_id": group_id,
        "currency": "PKR",
        "total_group_spending": money(total_spending),
        "current_user_total_paid": money(total_paid),
        "current_user_total_share": money(total_share),
        "current_balance": balance,
        "amount_user_owes": max(-balance, ZERO),
        "amount_owed_to_user": max(balance, ZERO),
        "unsettled_obligations": len(suggestions),
        "recent_expenses": recent,
    }
