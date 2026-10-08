from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.settlement import NotificationResponse
from app.services.notifications import list_notifications, mark_all_read, mark_read, unread_count

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def listing(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return list_notifications(db, current.id, offset, limit)


@router.get("/unread-count")
def count(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return {"unread_count": unread_count(db, current.id)}


@router.post("/{notification_id}/read")
def read(notification_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    mark_read(db, current.id, notification_id)
    return {"message": "Notification marked as read"}


@router.post("/read-all")
def read_all(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return {"updated": mark_all_read(db, current.id)}
