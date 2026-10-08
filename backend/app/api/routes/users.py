from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/search", response_model=list[UserPublic])
def search_users(
    q: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    query = q.strip()
    if not query:
        return []
    like = f"%{query}%"
    return list(
        db.scalars(
            select(User)
            .where(
                User.is_active.is_(True),
                User.id != current.id,
                or_(
                    User.full_name.ilike(like),
                    User.email.ilike(like),
                    User.phone_number.ilike(like),
                ),
            )
            .order_by(User.full_name)
            .limit(25)
        )
    )


@router.get("/{user_id}", response_model=UserPublic)
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    return user
