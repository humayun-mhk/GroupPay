import jwt
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import RegisterRequest


def register_user(db: Session, data: RegisterRequest) -> User:
    email = str(data.email).lower()
    existing = db.scalar(
        select(User).where(
            or_(User.email == email, User.phone_number == data.phone_number)
            if data.phone_number
            else User.email == email
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="An account with these details already exists")
    user = User(
        full_name=data.full_name,
        email=email,
        phone_number=data.phone_number,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect"
        )
    return user


def token_pair(user: User) -> dict:
    subject = str(user.id)
    return {
        "access_token": create_access_token(subject),
        "refresh_token": create_refresh_token(subject),
        "token_type": "bearer",
        "user": user,
    }


def refresh_user(db: Session, token: str) -> User:
    try:
        payload = decode_token(token, "refresh")
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired")
    return user
