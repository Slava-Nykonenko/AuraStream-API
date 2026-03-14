from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from core.dependencies import get_current_user
from database.models.user import UserModel
from database.session_postgresql import get_db
from schemas.social import (
    UserProfilesListSchema,
    UserProfileReadSchema,
    UserProfileCreateSchema
)
from services.social import SocialService

router = APIRouter(prefix="/social", tags=["users", "social"])

@router.get(
    "/profiles",
    response_model=UserProfilesListSchema
)
async def get_user_profiles(
        request: Request,
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    service = SocialService()
    return await service.list_profiles(
        request=request,
        db=db,
        page=page,
        per_page=per_page
    )


@router.get("/profiles/{profile_id}", response_model=UserProfileReadSchema)
async def get_user_profile(
        profile_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    return await SocialService.profile_retrieve(
        profile_id=profile_id,
        db=db
    )


@router.post("/me/profile", response_model=UserProfileReadSchema)
async def create_profile(
    profile_data: UserProfileCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    return await SocialService.create_user_profile(
        db, current_user, profile_data
    )
