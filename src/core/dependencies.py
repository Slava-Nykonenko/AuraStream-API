from typing import List

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models.user import UserModel, UserGroupEnum, UserProfileModel
from database.session_postgresql import get_db
from utils.tokens import decode_access_token


async def get_current_user(
        token: str,
        db: AsyncSession = Depends(get_db)
):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    user_id = payload.get("sub")
    user_stmt = (
        select(UserModel)
        .options(selectinload(UserModel.group))
        .where(UserModel.id == int(user_id))
    )
    result = await db.execute(user_stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_user_optional(
        db: AsyncSession = Depends(get_db),
        token: str | None = None
):
    return await get_current_user(token, db) if token else None


async def get_user_by_email(
        email: str,
        db: AsyncSession
) -> UserModel:
    stmt = select(UserModel).where(UserModel.email == email)
    return await db.scalar(stmt)


async def get_current_user_with_profile(
        user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    profile = await db.scalar(
        select(UserProfileModel).where(UserProfileModel.user_id == user.id)
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profile required to perform this action."
        )
    user.profile = profile
    return user


class RoleChecker:
    def __init__(self, allowed_roles: List[UserGroupEnum]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: UserModel = Depends(get_current_user)):
        if user.group.name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have enough permissions to access this resource."
            )
        return user
