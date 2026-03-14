from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import (
    RoleChecker,
    get_current_user,
    get_current_user_optional,
    get_current_user_with_profile
)
from database.models.user import UserGroupEnum, UserModel
from database.session_postgresql import get_db
from schemas.movies import (
    MovieListResponseSchema,
    MovieReadSchema,
    MovieCreateRequestSchema,
    MovieUpdateRequestSchema,
    GenresListSchema,
    MovieFilterParams,
    MovieDetailBase,
    MovieRatingResponseSchema,
    MovieRatingPayloadSchema,
)
from schemas.social import (
    SocialActionResponseSchema,
    CommentReadSchema,
    CommentCreateSchema,
    ReplyCreateSchema
)
from services.movies import MovieService
from services.social import SocialService

router = APIRouter(prefix="/movie_theater", tags=["movies"])


allow_moderator_plus = RoleChecker(
    [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]
)
allow_admin_only = RoleChecker([UserGroupEnum.ADMIN])


@router.get("/movies", response_model=MovieListResponseSchema)
async def get_movies(
        request: Request,
        db: AsyncSession = Depends(get_db),
        params: MovieFilterParams = Depends(),
        current_user: UserModel = Depends(get_current_user),
):
    if params.only_favorites and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You must be logged in to view your favorites."
        )
    service = MovieService()
    filters = params.model_dump(exclude={"page", "per_page", "sort_by"})
    result = await service.get_movies(
        request=request,
        db=db,
        filters=filters,
        page=params.page,
        per_page=params.per_page,
        sort_by=params.sort_by,
        user_id=current_user.id,
    )

    return result


@router.get("/movies/{movie_id}", response_model=MovieReadSchema)
async def get_movie(
        request: Request,
        movie_id: int,
        page: int = 1,
        per_page: int = 20,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user_optional),
):
    service = MovieService()
    user_id = current_user.id if current_user else None
    db_movie = await service.get_movie_by_id(
        movie_id=movie_id, user_id=user_id, db=db
    )
    if not db_movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )

    comments_pagination = await SocialService.get_movie_comments(
        db=db,
        movie_id=movie_id,
        page=page,
        per_page=per_page,
        request=request
    )
    movie_data = MovieDetailBase.model_validate(db_movie).model_dump()

    return MovieReadSchema(
        **movie_data,
        comments=comments_pagination
    )


@router.post("/movies", response_model=MovieReadSchema)
async def create_movie(
        movie_data: MovieCreateRequestSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_moderator_plus)
):
    service = MovieService()
    new_movie = await service.movie_create(movie_data=movie_data, db=db)
    return new_movie


@router.patch("/movies/{movie_id}", response_model=MovieReadSchema)
async def update_movie(
        movie_data: MovieUpdateRequestSchema,
        movie_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_moderator_plus)
):
    service = MovieService()
    return await service.movie_update(
        movie_id=movie_id,
        movie_data=movie_data,
        db=db
    )


@router.delete("/movies/{movie_id}", status_code=status.HTTP_200_OK)
async def delete_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(allow_moderator_plus)
):
    service = MovieService()
    deleted = await service.movie_delete(movie_id=movie_id, db=db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with ID {movie_id} not found."
        )
    return {"message": "Movie deleted."}


@router.get("/genres", response_model=GenresListSchema)
async def get_genres(
        request: Request,
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=50),
        name: str = Query(None)
):
    service = MovieService()
    response = await service.get_genres_list(
        request=request, db=db, page=page, per_page=per_page, name=name
    )
    return response


@router.post("/{movie_id}/favorite", response_model=SocialActionResponseSchema)
async def toggle_movie_favorite(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    service = SocialService()
    action = await service.toggle_favorite(db, current_user.id, movie_id)
    await db.commit()
    return {"status": "success", "message": f"Movie {action} favorites."}


@router.post("/{movie_id}/comments", response_model=CommentReadSchema)
async def post_comment(
    movie_id: int,
    payload: CommentCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    service = SocialService()
    comment = await service.add_comment(
        db, current_user.id, movie_id, payload.content
    )
    await db.commit()
    return comment


@router.post(
    "/movies/{movie_id}/comments/reply",
    response_model=CommentReadSchema
)
async def create_comment_reply(
        movie_id: int,
        reply_data: ReplyCreateSchema,
        db: AsyncSession = Depends(get_db),
        user: UserModel = Depends(get_current_user_with_profile)
):
    return await SocialService.create_reply(
        db=db,
        movie_id=movie_id,
        user=user,
        reply_data=reply_data
    )


@router.post(
    "/movies/{movie_id}/rate",
    response_model=MovieRatingResponseSchema
)
async def rate_movie(
    movie_id: int,
    payload: MovieRatingPayloadSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_with_profile)
):
    return await MovieService.rate_movie(
        db=db,
        movie_id=movie_id,
        user_id=current_user.id,
        score=payload.score
    )
