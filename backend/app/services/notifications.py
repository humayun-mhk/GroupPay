from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.settlement import Notification


def notify(db: Session, user_id: int, kind: str, title: str, message: str, entity_type: str | None = None, entity_id: int | None = None) -> None:
    db.add(Notification(user_id=user_id, type=kind, title=title, message=message, related_entity_type=entity_type, related_entity_id=entity_id))


def list_notifications(db: Session, user_id: int, offset: int = 0, limit: int = 50):
    return db.scalars(select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc(), Notification.id.desc()).offset(offset).limit(limit)).all()


def unread_count(db: Session, user_id: int) -> int:
    return db.scalar(select(func.count(Notification.id)).where(Notification.user_id == user_id, Notification.is_read.is_(False))) or 0


def mark_read(db: Session, user_id: int, notification_id: int) -> None:
    result = db.execute(update(Notification).where(Notification.id == notification_id, Notification.user_id == user_id).values(is_read=True))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=404, detail="Notification not found")
    db.commit()


def mark_all_read(db: Session, user_id: int) -> int:
    result = db.execute(update(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False)).values(is_read=True))
    db.commit()
    return result.rowcount or 0
