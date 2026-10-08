from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.friendship import FriendRequestResponse, FriendResponse
from app.services.friends import list_friends, list_requests, request_friend, respond

router = APIRouter(prefix="/friends", tags=["friends"])


@router.post(
    "/requests/{user_id}", response_model=FriendRequestResponse, status_code=status.HTTP_201_CREATED
)
def send_request(
    user_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    return request_friend(db, current, user_id)


@router.get("/requests/incoming", response_model=list[FriendRequestResponse])
def incoming(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return list_requests(db, current.id, True)


@router.get("/requests/outgoing", response_model=list[FriendRequestResponse])
def outgoing(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return list_requests(db, current.id, False)


@router.post("/requests/{request_id}/accept", response_model=FriendRequestResponse)
def accept(
    request_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    return respond(db, current, request_id, True)


@router.post("/requests/{request_id}/reject", response_model=FriendRequestResponse)
def reject(
    request_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    return respond(db, current, request_id, False)


@router.get("", response_model=list[FriendResponse])
def friends(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return [
        {"friendship_id": friendship.id, "user": user, "since": friendship.updated_at}
        for friendship, user in list_friends(db, current.id)
    ]
