from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.group_member import GroupRole
from app.schemas.common import UserPublic


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Group name must contain at least 2 characters")
        return value


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Group name cannot be empty")
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Group name must contain at least 2 characters")
        return value


class GroupMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    role: GroupRole
    joined_at: datetime
    user: UserPublic


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime
    current_user_role: GroupRole
    members_count: int


class GroupDetails(GroupResponse):
    members: list[GroupMemberResponse]


class AddMemberRequest(BaseModel):
    user_id: int


class RoleUpdate(BaseModel):
    role: GroupRole
