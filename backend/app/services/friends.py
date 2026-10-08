from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.friendship import Friendship, FriendshipStatus
from app.models.user import User
from app.services.notifications import notify


def request_friend(db: Session, requester: User, receiver_id: int) -> Friendship:
    if requester.id == receiver_id:
        raise HTTPException(status_code=400, detail="You cannot send a friend request to yourself")
    receiver = db.get(User, receiver_id)
    if receiver is None or not receiver.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.scalar(
        select(Friendship).where(
            or_(
                and_(
                    Friendship.requester_id == requester.id, Friendship.receiver_id == receiver_id
                ),
                and_(
                    Friendship.requester_id == receiver_id, Friendship.receiver_id == requester.id
                ),
            )
        )
    )
    if existing and existing.status in (FriendshipStatus.PENDING, FriendshipStatus.ACCEPTED):
        raise HTTPException(status_code=409, detail="A friend request or friendship already exists")
    if existing:
        existing.requester_id = requester.id
        existing.receiver_id = receiver_id
        existing.status = FriendshipStatus.PENDING
        db.commit()
        db.refresh(existing)
        return existing
    friendship = Friendship(requester_id=requester.id, receiver_id=receiver_id)
    db.add(friendship)
    db.flush()
    notify(db, receiver_id, "FRIEND_REQUEST", "New friend request", f"{requester.full_name} sent you a friend request.", "friendship", friendship.id)
    db.commit()
    db.refresh(friendship)
    return friendship


def list_requests(db: Session, user_id: int, incoming: bool) -> list[Friendship]:
    field = Friendship.receiver_id if incoming else Friendship.requester_id
    return list(
        db.scalars(
            select(Friendship)
            .options(joinedload(Friendship.requester), joinedload(Friendship.receiver))
            .where(field == user_id, Friendship.status == FriendshipStatus.PENDING)
            .order_by(Friendship.created_at.desc())
        ).unique()
    )


def respond(db: Session, user: User, request_id: int, accepted: bool) -> Friendship:
    friendship = db.get(Friendship, request_id)
    if (
        friendship is None
        or friendship.receiver_id != user.id
        or friendship.status != FriendshipStatus.PENDING
    ):
        raise HTTPException(status_code=404, detail="Friend request not found")
    friendship.status = FriendshipStatus.ACCEPTED if accepted else FriendshipStatus.REJECTED
    if accepted:
        notify(db, friendship.requester_id, "FRIEND_ACCEPTED", "Friend request accepted", f"{user.full_name} accepted your friend request.", "friendship", friendship.id)
    db.commit()
    db.refresh(friendship)
    return friendship


def list_friends(db: Session, user_id: int) -> list[tuple[Friendship, User]]:
    rows = db.execute(
        select(Friendship, User)
        .join(
            User,
            or_(
                and_(Friendship.requester_id == user_id, User.id == Friendship.receiver_id),
                and_(Friendship.receiver_id == user_id, User.id == Friendship.requester_id),
            ),
        )
        .where(Friendship.status == FriendshipStatus.ACCEPTED)
        .order_by(Friendship.updated_at.desc())
    ).all()
    return [(friendship, friend) for friendship, friend in rows]


def are_friends(db: Session, user_a: int, user_b: int) -> bool:
    return (
        db.scalar(
            select(Friendship.id).where(
                Friendship.status == FriendshipStatus.ACCEPTED,
                or_(
                    and_(Friendship.requester_id == user_a, Friendship.receiver_id == user_b),
                    and_(Friendship.requester_id == user_b, Friendship.receiver_id == user_a),
                ),
            )
        )
        is not None
    )
