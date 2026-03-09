import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from core.settings import settings
from database.models.user import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel
)

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
