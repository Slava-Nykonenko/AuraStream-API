import secrets
from datetime import datetime, timedelta, timezone, UTC
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from core.settings import settings
from database.models.user import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel
)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_activation_token(db: AsyncSession, user_id: int) -> str:
    """Generates a 32-byte secure token valid for 24 hours."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(
        hours=settings.ACTIVATION_TOKEN_EXPIRE_HOURS
    )
    new_token = ActivationTokenModel(
        user_id=user_id,
        token=token,
        expires_at=expires.replace(tzinfo=None)
    )
    db.add(new_token)
    return token


async def create_password_reset_token(db: AsyncSession, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
    )
    new_token = PasswordResetTokenModel(
        user_id=user_id,
        token=token,
        expires_at=expires.replace(tzinfo=None)
    )
    db.add(new_token)
    return new_token.token


async def create_refresh_token(db: AsyncSession, user_id: int) -> str:
    token = secrets.token_urlsafe(64)
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    new_token = RefreshTokenModel(
        user_id=user_id,
        token=token,
        expires_at=expires.replace(tzinfo=None)
    )
    db.add(new_token)
    return new_token.token


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
