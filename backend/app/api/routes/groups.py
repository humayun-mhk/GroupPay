from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.user import User
from app.schemas.common import Message
from app.schemas.group import (
    AddMemberRequest,
    GroupCreate,
    GroupDetails,
    GroupMemberResponse,
    GroupResponse,
    GroupUpdate,
    RoleUpdate,
)
from app.services.groups import (
    add_member,
    create_group,
    group_details,
    member_for,
    remove_member,
    require_admin,
    require_member,
    update_member_role,
    visible_groups,
)

router = APIRouter(prefix="/groups", tags=["groups"])


def group_summary(group, member, count):
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "created_by": group.created_by,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
        "current_user_role": member.role,
        "members_count": count,
    }


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create(
    data: GroupCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    group = create_group(db, current, data.name, data.description)
    return group_summary(group, member_for(db, group.id, current.id), 1)


@router.get("", response_model=list[GroupResponse])
def list_groups(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return [group_summary(*row) for row in visible_groups(db, current.id)]


@router.get("/{group_id}", response_model=GroupDetails)
def detail(group_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    require_member(db, group_id, current.id)
    group = db.get(Group, group_id)
    group = group_details(db, group)
    member = member_for(db, group_id, current.id)
    return {**group_summary(group, member, len(group.members)), "members": group.members}


@router.patch("/{group_id}", response_model=GroupResponse)
def update(
    group_id: int,
    data: GroupUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    require_admin(db, group_id, current.id)
    group = db.get(Group, group_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(group, key, " ".join(value.split()) if key == "name" and value else value)
    db.commit()
    db.refresh(group)
    return group_summary(group, member_for(db, group_id, current.id), len(group.members))


@router.post(
    "/{group_id}/members", response_model=GroupMemberResponse, status_code=status.HTTP_201_CREATED
)
def add_group_member(
    group_id: int,
    data: AddMemberRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return add_member(db, group, data.user_id, current.id)


@router.get("/{group_id}/members", response_model=list[GroupMemberResponse])
def members(
    group_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    require_member(db, group_id, current.id)
    return db.query(GroupMember).filter(GroupMember.group_id == group_id).all()


@router.patch("/{group_id}/members/{user_id}", response_model=GroupMemberResponse)
def change_member_role(
    group_id: int,
    user_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if db.get(Group, group_id) is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return update_member_role(db, group_id, user_id, current.id, data.role)


@router.delete("/{group_id}/members/{user_id}", response_model=Message)
def remove_group_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    remove_member(db, group, user_id, current.id)
    return {"message": "Member removed"}
