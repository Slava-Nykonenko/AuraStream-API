import secrets
from datetime import UTC, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_user_by_email
from core.settings import settings
from database.models.user import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    RefreshTokenModel,
    ActivationTokenModel,
    PasswordResetTokenModel
)
from schemas.user import (
    UserCreateRequest,
    LoginSchema,
    RefreshTokenRequest,
    PasswordResetCompleteSchema,
    ChangePasswordSchema
)
from tasks.email_tasks import send_email
from utils.tokens import (
    hash_password,
    create_activation_token,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_password_reset_token
)

BASE_URL = settings.BASE_URL + "/auth"


class AuthServices:

    @staticmethod
    async def create_activation_link(user: UserModel, db: AsyncSession):
        token = await create_activation_token(db, user.id)

        activation_link = f"{BASE_URL}/activate?token={token}"
        body_data = {
            "activation_url": activation_link,
            "expires_in": settings.ACTIVATION_TOKEN_EXPIRE_HOURS
        }
        send_email.delay(
            email=user.email,
            body_data=body_data,
            msg_type="activation",
        )
        return None

    async def sign_up(self, payload: UserCreateRequest, db: AsyncSession):
        email = payload.email.lower()
        existing_user_stmt = select(UserModel).where(
            UserModel.email == email)
        existing_user = await db.scalar(existing_user_stmt)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists."
            )

        group_stmt = select(UserGroupModel).where(
            UserGroupModel.name == UserGroupEnum.USER
        )
        group = await db.scalar(group_stmt)
        new_user = UserModel(
            email=email,
            hashed_password=hash_password(payload.password),
            group_id=group.id,
            is_active=False
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        await self.create_activation_link(user=new_user, db=db)
        return True

    @staticmethod
    async def sign_in(payload: LoginSchema, db: AsyncSession):
        result = await db.execute(
            select(UserModel).where(UserModel.email == payload.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(
                payload.password, user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not activated. Please check your email."
            )

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        refresh_token = await create_refresh_token(db, user.id)
        await db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    @staticmethod
    async def _perform_user_activation(
            user: UserModel,
            db: AsyncSession
    ):
        user.is_active = True

        token_stmt = delete(ActivationTokenModel).where(
            ActivationTokenModel.user_id == user.id)
        await db.execute(token_stmt)

        await db.flush()
        return user


    @staticmethod
    async def refresh_token_pair(
            payload: RefreshTokenRequest,
            db: AsyncSession
    ):
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.token == payload.refresh_token)
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()

        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        if db_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            await db.delete(db_token)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired. Please login again."
            )

        user_stmt = select(UserModel).where(UserModel.id == db_token.user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User inactive or not found"
            )

        new_access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email})

        new_refresh_token_str = secrets.token_urlsafe(64)
        db_token.token = new_refresh_token_str
        exp_date = datetime.now(UTC) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        db_token.expires_at = exp_date.replace(tzinfo=None)

        await db.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token_str,
            "token_type": "bearer"
        }

    async def activate_user_by_token(self, token: str, db: AsyncSession):
        stmt = select(ActivationTokenModel).where(
            ActivationTokenModel.token == token)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or used activation token.")

        if token_record.expires_at < datetime.now(UTC).replace(tzinfo=None):
            await db.delete(token_record)
            await db.flush()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Activation link has expired."
            )

        user_stmt = select(UserModel).where(
            UserModel.id == token_record.user_id
        )
        user_result = await db.execute(user_stmt)
        user = user_result.scalar()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        return await self._perform_user_activation(user, db)

    @staticmethod
    async def user_logout(
            payload: RefreshTokenRequest,
            current_user: UserModel,
            db: AsyncSession
    ):
        stmt = delete(RefreshTokenModel).where(
            RefreshTokenModel.token == payload.refresh_token,
            RefreshTokenModel.user_id == current_user.id
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def change_password(
            payload: ChangePasswordSchema,
            user: UserModel,
            db: AsyncSession
    ):
        if not verify_password(payload.old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect old password."
            )
        user.hashed_password = hash_password(payload.password)
        await db.commit()

        body_data = {
            "login_link": f"{BASE_URL}/login"
        }
        send_email.delay(
            email=user.email,
            body_data=body_data,
            msg_type="reset_pass_success",
        )
        return True

    @staticmethod
    async def reset_password(email: str, db: AsyncSession):
        user = await get_user_by_email(email=email, db=db)
        reset_token = await create_password_reset_token(db=db, user_id=user.id)

        reset_link = f"{BASE_URL}/password-reset-confirm?token={reset_token}"
        body_data = {
            "reset_link": reset_link,
            "expires_in": settings.RESET_TOKEN_EXPIRE_MINUTES
        }
        send_email.delay(
            email=user.email,
            body_data=body_data,
            msg_type="reset_pass",
        )
        return None

    @staticmethod
    async def reset_password_confirm(
            data: PasswordResetCompleteSchema,
            db: AsyncSession
    ):
        stmt = select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token == data.token
        )
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or already used reset token."
            )

        if token_record.expires_at < datetime.now(timezone.utc).replace(
                tzinfo=None):
            await db.delete(token_record)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset link has expired."
            )

        user = await db.get(UserModel, token_record.user_id)
        if not user:
            await db.delete(token_record)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        user.hashed_password = hash_password(data.password)
        user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        await db.delete(token_record)
        await db.commit()

        body_data = {
            "login_link": f"{BASE_URL}/login"
        }
        send_email.delay(
            email=user.email,
            body_data=body_data,
            msg_type="reset_pass_success",
        )

    @staticmethod
    async def change_user_group(
            user: UserModel,
            user_group: UserGroupEnum,
            db: AsyncSession
    ):
        group_stmt = select(UserGroupModel).where(
            UserGroupModel.name == user_group
        )
        group_result = await db.execute(group_stmt)
        group_db = group_result.scalar_one_or_none()
        user.group_id = group_db.id
        user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.flush()
        return user
