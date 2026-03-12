from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import RoleChecker
from database.models.user import UserGroupEnum, UserModel
from database.session_postgresql import get_db
from schemas.movies import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieReadSchema,
    MovieCreateRequestSchema,
    MovieUpdateRequestSchema,
    GenresListSchema,
    MovieFilterParams,
)
from services.movies import MovieService, generate_page_link

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
):
    service = MovieService()
    filters = params.model_dump(exclude={"page", "per_page", "sort_by"})
    movies, total_items = await service.get_movies(
        db=db,
        filters=filters,
        page=params.page,
        per_page=params.per_page,
        sort_by=params.sort_by
    )
    total_pages = (total_items + params.per_page - 1) // params.per_page
    prev_page = await generate_page_link(
            request, params.page - 1, params.per_page
        ) if params.page > 1 else None
    next_page = await generate_page_link(
            request, params.page + 1, params.per_page
        ) if params.page < total_pages else None
    return MovieListResponseSchema(
        movies=[MovieListItemSchema.model_validate(m) for m in movies],
        total_pages=total_pages,
        total_items=total_items,
        prev_page=prev_page,
        next_page=next_page
    )


@router.get("/movies/{movie_id}", response_model=MovieReadSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    service = MovieService()
    db_movie = await service.get_movie_by_id(movie_id=movie_id, db=db)
    if not db_movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )
    return db_movie


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
