from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.settlement import SettlementStatus
from app.schemas.common import UserPublic


class SettlementCreate(BaseModel):
    payer_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    note: str | None = Field(default=None, max_length=240)


class SettlementEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: int
    action: str
    note: str | None
    created_at: datetime


class SettlementResponse(BaseModel):
    id: int
    group_id: int
    group_name: str
    requester: UserPublic
    payer: UserPublic
    amount: Decimal
    status: SettlementStatus
    note: str | None
    source_type: str
    created_at: datetime
    updated_at: datetime
    claimed_paid_at: datetime | None
    confirmed_at: datetime | None
    rejected_at: datetime | None
    events: list[SettlementEventResponse]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    title: str
    message: str
    related_entity_type: str | None
    related_entity_id: int | None
    is_read: bool
    created_at: datetime
