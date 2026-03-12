from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_auth_service
from core.dependencies import RoleChecker, get_user_by_email
from database.models.user import UserGroupEnum, UserModel, ActivationTokenModel
from database.session_postgresql import get_db
from schemas.user import ChangeUserGroupSchema, MessageSchema, UserBase
from services.auth_user import AuthServices

router = APIRouter(prefix="/admin", tags=["admin"])

allow_admin_only = RoleChecker([UserGroupEnum.ADMIN])

@router.patch("/change-user-status", response_model=MessageSchema)
async def change_user_status(
        payload: ChangeUserGroupSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_admin_only),
        auth_service: AuthServices = Depends(get_auth_service)
):
    user_db = await get_user_by_email(payload.email, db=db)
    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    user = await auth_service.change_user_group(
        user=user_db, user_group=payload.user_group, db=db
    )
    await db.commit()
    await db.refresh(user)

    return MessageSchema(
        message=f"User with ID {user.id} (email: {user.email}) has been moved "
                f"into the {payload.user_group.name} group."
    )


@router.patch("/activate-user", response_model=MessageSchema)
async def admin_activate_user(
        payload: UserBase,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_admin_only),
        auth_service: AuthServices = Depends(get_auth_service)
):
    user_db = await get_user_by_email(payload.email, db=db)

    if not user_db:
        raise HTTPException(status_code=404, detail="User not found.")
    if user_db.is_active:
        return MessageSchema(message="User is already active.")

    await auth_service._perform_user_activation(user_db, db)
    await db.commit()

    return MessageSchema(message=f"User {user_db.email} activated by admin.")
