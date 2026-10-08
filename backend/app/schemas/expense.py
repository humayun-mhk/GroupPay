from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.expense import SplitType
from app.schemas.common import UserPublic


class SplitParticipantInput(BaseModel):
    user_id: int
    amount: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)
    percentage: Decimal | None = Field(default=None, max_digits=7, decimal_places=4)
    shares: Decimal | None = Field(default=None, max_digits=12, decimal_places=4)


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    total_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: Literal["PKR"] = "PKR"
    paid_by_user_id: int
    split_type: SplitType = SplitType.EQUAL
    expense_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    participants: list[SplitParticipantInput] = Field(min_length=1, max_length=100)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Expense title must contain at least 2 characters")
        return value

    @model_validator(mode="after")
    def unique_participants(self):
        ids = [item.user_id for item in self.participants]
        if len(ids) != len(set(ids)):
            raise ValueError("Participants cannot be duplicated")
        return self


class ExpenseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    total_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    currency: Literal["PKR"] | None = None
    paid_by_user_id: int | None = None
    split_type: SplitType | None = None
    expense_date: datetime | None = None
    participants: list[SplitParticipantInput] | None = Field(
        default=None, min_length=1, max_length=100
    )

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Expense title cannot be empty")
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Expense title must contain at least 2 characters")
        return value

    @model_validator(mode="after")
    def unique_participants(self):
        if self.participants is not None:
            ids = [item.user_id for item in self.participants]
            if len(ids) != len(set(ids)):
                raise ValueError("Participants cannot be duplicated")
        return self


class ExpenseParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    amount_owed: Decimal
    percentage: Decimal | None
    shares: Decimal | None
    user: UserPublic


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    group_id: int
    title: str
    description: str | None
    total_amount: Decimal
    currency: str
    paid_by_user_id: int
    payer: UserPublic
    split_type: SplitType
    expense_date: datetime
    created_by: int
    created_at: datetime
    updated_at: datetime
    participants: list[ExpenseParticipantResponse]


class ExpensePage(BaseModel):
    items: list[ExpenseResponse]
    total: int
    offset: int
    limit: int


class SplitAllocationResponse(BaseModel):
    user_id: int
    amount_owed: Decimal
    percentage: Decimal | None = None
    shares: Decimal | None = None


class ExpensePreviewResponse(BaseModel):
    total_amount: Decimal
    currency: str
    split_type: SplitType
    allocations: list[SplitAllocationResponse]


class BalanceLine(BaseModel):
    user: UserPublic
    net_balance: Decimal
    amount_owed: Decimal
    amount_owed_to_user: Decimal


class SettlementSuggestion(BaseModel):
    from_user: UserPublic
    to_user: UserPublic
    amount: Decimal
    currency: str = "PKR"


class GroupSummary(BaseModel):
    group_id: int
    currency: str = "PKR"
    total_group_spending: Decimal
    current_user_total_paid: Decimal
    current_user_total_share: Decimal
    current_balance: Decimal
    amount_user_owes: Decimal
    amount_owed_to_user: Decimal
    unsettled_obligations: int
    recent_expenses: list[ExpenseResponse]
