from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SettlementStatus(str, Enum):
    PENDING = "PENDING"
    PAYMENT_CLAIMED = "PAYMENT_CLAIMED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class SettlementRequest(Base):
    __tablename__ = "settlement_requests"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_settlement_positive_amount"),
        Index("ix_settlement_group_status_created", "group_id", "status", "created_at"),
        Index("ix_settlement_payer_status", "payer_id", "status"),
        Index("ix_settlement_requester_created", "requester_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    # In this MVP the requester is also the receiver/creditor.
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    payer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[SettlementStatus] = mapped_column(SAEnum(SettlementStatus, native_enum=False), nullable=False, default=SettlementStatus.PENDING, index=True)
    note: Mapped[str | None] = mapped_column(String(240))
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    source_reference_id: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    claimed_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    group = relationship("Group")
    requester = relationship("User", foreign_keys=[requester_id])
    payer = relationship("User", foreign_keys=[payer_id])
    events = relationship("SettlementEvent", cascade="all, delete-orphan", order_by="SettlementEvent.created_at")

    @property
    def group_name(self) -> str:
        return self.group.name


class SettlementEvent(Base):
    __tablename__ = "settlement_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_request_id: Mapped[int] = mapped_column(ForeignKey("settlement_requests.id", ondelete="CASCADE"), index=True, nullable=False)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actor = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notification_user_read_created", "user_id", "is_read", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(String(300), nullable=False)
    related_entity_type: Mapped[str | None] = mapped_column(String(40))
    related_entity_id: Mapped[int | None] = mapped_column()
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user = relationship("User")
