from fastapi import (
    HTTPException,
    Depends,
    APIRouter,
    status
)
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_auth_service, get_current_user
from database.models.user import (
    UserModel,
    ActivationTokenModel,
)
from database.session_postgresql import get_db
from schemas.user import (
    UserCreateRequest,
    TokenPairResponse,
    RefreshTokenRequest,
    LoginSchema,
    MessageSchema,
    PasswordResetCompleteSchema
)
from services.auth_user import AuthServices

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@router.post("/register", response_model=MessageSchema)
async def register_user(
        payload: UserCreateRequest,
        db: AsyncSession = Depends(get_db),
        auth_service: AuthServices = Depends(get_auth_service)
):
    new_user = await auth_service.sign_up(payload=payload, db=db)
    if new_user:
        return MessageSchema(
            message="An activation link has sent to your email."
        )


@router.get("/activate", response_model=MessageSchema)
async def activate_account(
        token: str,
        db: AsyncSession = Depends(get_db),
        auth_service: AuthServices = Depends(get_auth_service)
):
    user = await auth_service.activate_user(token=token, db=db)
    if user:
        return MessageSchema(
            message="Account successfully activated! You can now log in."
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found."
    )


@router.post("/refresh-activation-link", response_model=MessageSchema)
async def refresh_activation_link(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        auth_service: AuthServices = Depends(get_auth_service)
):
    await db.execute(
        delete(ActivationTokenModel).where(
            ActivationTokenModel.user_id == user_id
        )
    )
    user = await db.scalar(select(UserModel).where(UserModel.id == user_id))
    await auth_service.create_activation_link(user=user, db=db)
    return MessageSchema(message="A new activation link sent to your email.")


@router.post("/login", response_model=TokenPairResponse)
async def login(
        payload: LoginSchema,
        db: AsyncSession = Depends(get_db),
        auth_service: AuthServices = Depends(get_auth_service)
):
    token_pair = await auth_service.sign_in(payload=payload, db=db)
    return token_pair


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh_access_token(
        payload: RefreshTokenRequest,
        db: AsyncSession = Depends(get_db),
        auth_service: AuthServices = Depends(get_auth_service)
):
    token_pair = await auth_service.refresh_token_pair(payload=payload, db=db)
    return token_pair


@router.post("/logout", response_model=MessageSchema)
async def logout(
        payload: RefreshTokenRequest,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user),
        auth_service: AuthServices = Depends(get_auth_service)
):
    result = await auth_service.user_logout(
        payload=payload,
        current_user=current_user,
        db=db
    )

    if result == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    return MessageSchema(message="Successfully logged out")


@router.post("/password-reset-request", response_model=MessageSchema)
async def request_password_reset(
        email: str,
        db: AsyncSession = Depends(get_db),
        auth_service: AuthServices = Depends(get_auth_service)
):
    await auth_service.reset_password(email=email, db=db)
    return MessageSchema(
        message="If the account exists, a reset email has been sent."
    )


@router.post("/password-reset-confirm", response_model=MessageSchema)
async def confirm_password_reset(
        data: PasswordResetCompleteSchema,
        db: AsyncSession = Depends(get_db),
        auth_service: AuthServices = Depends(get_auth_service)
):
    await auth_service.reset_password_confirm(data=data, db=db)

    return MessageSchema(message="Password updated successfully.")
