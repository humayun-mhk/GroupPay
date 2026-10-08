from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.friendship import FriendshipStatus
from app.schemas.common import UserPublic


class FriendRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: FriendshipStatus
    created_at: datetime
    requester: UserPublic
    receiver: UserPublic


class FriendResponse(BaseModel):
    friendship_id: int
    user: UserPublic
    since: datetime
