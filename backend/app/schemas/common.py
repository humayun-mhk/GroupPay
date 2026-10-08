from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    avatar_url: str | None = None


class UserPrivate(UserPublic):
    email: EmailStr
    phone_number: str | None = None
    is_active: bool
    created_at: datetime


class Message(BaseModel):
    message: str
