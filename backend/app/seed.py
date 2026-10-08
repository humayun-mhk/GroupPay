from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.expense import Expense, ExpenseParticipant, SplitType
from app.models.friendship import Friendship, FriendshipStatus
from app.models.group import Group
from app.models.group_member import GroupMember, GroupRole
from app.models.settlement import Notification, SettlementEvent, SettlementRequest, SettlementStatus
from app.models.user import User
from app.services.expense_calculator import SplitInput, calculate_split


def seed():
    with SessionLocal() as db:
        existing = db.scalar(select(User).limit(1))
        if existing:
            print("Database already contains users; seed skipped.")
            return
        users = [
            User(
                full_name=name,
                email=email,
                phone_number=phone,
                password_hash=hash_password("GroupPay123!"),
            )
            for name, email, phone in [
                ("Humayun Ahmed", "humayun@example.com", "+923001234567"),
                ("Ali Khan", "ali@example.com", "+923111234567"),
                ("Hamza Raza", "hamza@example.com", "+923211234567"),
                ("Ahmed Ali", "ahmed@example.com", "+923221234567"),
                ("Usman Tariq", "usman@example.com", "+923231234567"),
            ]
        ]
        db.add_all(users)
        db.flush()
        db.add_all(
            [
                Friendship(
                    requester_id=users[0].id,
                    receiver_id=users[1].id,
                    status=FriendshipStatus.ACCEPTED,
                ),
                Friendship(
                    requester_id=users[0].id,
                    receiver_id=users[2].id,
                    status=FriendshipStatus.ACCEPTED,
                ),
                Friendship(requester_id=users[1].id, receiver_id=users[2].id, status=FriendshipStatus.ACCEPTED),
                Friendship(requester_id=users[1].id, receiver_id=users[3].id, status=FriendshipStatus.ACCEPTED),
                Friendship(requester_id=users[1].id, receiver_id=users[4].id, status=FriendshipStatus.ACCEPTED),
            ]
        )
        group = Group(
            name="Dinner Friends",
            description="Shared dinners and city plans",
            created_by=users[0].id,
        )
        db.add(group)
        db.flush()
        db.add_all(
            [
                GroupMember(group_id=group.id, user_id=users[0].id, role=GroupRole.ADMIN),
                *[GroupMember(group_id=group.id, user_id=user.id, role=GroupRole.MEMBER) for user in users[1:]],
            ]
        )
        db.flush()

        def expense(title, total, payer, participants):
            allocations = calculate_split(Decimal(total), SplitType.EQUAL, [SplitInput(user_id=user.id) for user in participants])
            item = Expense(group_id=group.id, title=title, total_amount=Decimal(total), currency="PKR", paid_by_user_id=payer.id, split_type=SplitType.EQUAL, expense_date=datetime.now(timezone.utc), created_by=payer.id)
            db.add(item)
            db.flush()
            db.add_all([ExpenseParticipant(expense_id=item.id, user_id=part.user_id, amount_owed=part.amount_owed) for part in allocations])
            return item

        expense("Dinner", "5000.00", users[0], users)
        expense("Taxi to the restaurant", "2000.00", users[1], [users[1], users[2]])
        expense("Late-night chai", "1200.00", users[3], [users[3], users[1]])

        def settlement(requester, payer, amount, status):
            request = SettlementRequest(group_id=group.id, requester_id=requester.id, payer_id=payer.id, amount=Decimal(amount), status=status, note="Dinner", source_type="MANUAL")
            db.add(request)
            db.flush()
            db.add(SettlementEvent(settlement_request_id=request.id, actor_id=requester.id, action="PENDING", note="Dinner"))
            if status in (SettlementStatus.PAYMENT_CLAIMED, SettlementStatus.CONFIRMED):
                db.add(SettlementEvent(settlement_request_id=request.id, actor_id=payer.id, action="PAYMENT_CLAIMED"))
                request.claimed_paid_at = datetime.now(timezone.utc)
            if status == SettlementStatus.CONFIRMED:
                db.add(SettlementEvent(settlement_request_id=request.id, actor_id=requester.id, action="CONFIRMED"))
                request.confirmed_at = datetime.now(timezone.utc)
            if status in (SettlementStatus.PENDING, SettlementStatus.PAYMENT_CLAIMED):
                db.add(Notification(user_id=payer.id, type="PAYMENT_REQUEST", title="Payment requested", message=f"{requester.full_name} requested Rs. {amount} in {group.name}.", related_entity_type="settlement", related_entity_id=request.id))
                if status == SettlementStatus.PAYMENT_CLAIMED:
                    db.add(Notification(user_id=requester.id, type="PAYMENT_CLAIMED", title="Payment marked as paid", message=f"{payer.full_name} says they paid Rs. {amount}.", related_entity_type="settlement", related_entity_id=request.id))
            elif status == SettlementStatus.CONFIRMED:
                db.add(Notification(user_id=payer.id, type="PAYMENT_CONFIRMED", title="Payment confirmed", message=f"{requester.full_name} confirmed Rs. {amount}.", related_entity_type="settlement", related_entity_id=request.id))
            return request

        settlement(users[0], users[2], "500.00", SettlementStatus.CONFIRMED)
        settlement(users[0], users[3], "400.00", SettlementStatus.PENDING)
        settlement(users[0], users[4], "500.00", SettlementStatus.PAYMENT_CLAIMED)
        db.commit()
        print("Seeded Dinner Friends with 5 users, 3 expenses, and confirmed/pending/claimed settlements. Password for all: GroupPay123!")


if __name__ == "__main__":
    seed()
