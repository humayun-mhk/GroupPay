from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.group import Group
from app.models.group_member import GroupMember, GroupRole
from app.models.user import User
from app.services.friends import are_friends
from app.services.notifications import notify


def member_for(db: Session, group_id: int, user_id: int) -> GroupMember | None:
    return db.scalar(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    )


def require_member(db: Session, group_id: int, user_id: int) -> GroupMember:
    member = member_for(db, group_id, user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return member


def require_admin(db: Session, group_id: int, user_id: int) -> GroupMember:
    member = require_member(db, group_id, user_id)
    if member.role != GroupRole.ADMIN:
        raise HTTPException(status_code=403, detail="Group admin role required")
    return member


def create_group(db: Session, creator: User, name: str, description: str | None) -> Group:
    group = Group(name=name, description=description, created_by=creator.id)
    db.add(group)
    db.flush()
    db.add(GroupMember(group_id=group.id, user_id=creator.id, role=GroupRole.ADMIN))
    db.commit()
    db.refresh(group)
    return group


def add_member(db: Session, group: Group, user_id: int, actor_id: int) -> GroupMember:
    require_admin(db, group.id, actor_id)
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    if member_for(db, group.id, user_id):
        raise HTTPException(status_code=409, detail="User is already a group member")
    if not are_friends(db, actor_id, user_id):
        raise HTTPException(status_code=400, detail="You can only add accepted friends")
    membership = GroupMember(group_id=group.id, user_id=user_id, role=GroupRole.MEMBER)
    db.add(membership)
    notify(db, user_id, "GROUP_ADDED", "Added to a group", f'You were added to "{group.name}".', "group", group.id)
    db.commit()
    db.refresh(membership)
    return membership


def remove_member(db: Session, group: Group, user_id: int, actor_id: int) -> None:
    require_admin(db, group.id, actor_id)
    target = member_for(db, group.id, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Group member not found")
    if target.role == GroupRole.ADMIN:
        count = len(
            db.scalars(
                select(GroupMember.id).where(
                    GroupMember.group_id == group.id, GroupMember.role == GroupRole.ADMIN
                )
            ).all()
        )
        if count <= 1:
            raise HTTPException(status_code=400, detail="A group must have at least one admin")
    db.delete(target)
    db.commit()


def update_member_role(
    db: Session, group_id: int, user_id: int, actor_id: int, role: GroupRole
) -> GroupMember:
    require_admin(db, group_id, actor_id)
    target = member_for(db, group_id, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Group member not found")
    if target.role == GroupRole.ADMIN and role == GroupRole.MEMBER:
        admin_ids = db.scalars(
            select(GroupMember.id).where(
                GroupMember.group_id == group_id, GroupMember.role == GroupRole.ADMIN
            )
        ).all()
        if len(admin_ids) <= 1:
            raise HTTPException(status_code=400, detail="A group must have at least one admin")
    target.role = role
    db.commit()
    db.refresh(target)
    return target


def visible_groups(db: Session, user_id: int) -> list[tuple[Group, GroupMember, int]]:
    rows = db.execute(
        select(Group, GroupMember)
        .options(selectinload(Group.members))
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user_id)
        .order_by(Group.updated_at.desc())
    ).all()
    return [(group, member, len(group.members)) for group, member in rows]


def group_details(db: Session, group: Group) -> Group:
    return (
        db.execute(
            select(Group)
            .options(joinedload(Group.members).joinedload(GroupMember.user))
            .where(Group.id == group.id)
        )
        .unique()
        .scalar_one()
    )
