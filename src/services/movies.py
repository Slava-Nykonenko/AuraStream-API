import uuid
from typing import Type

from fastapi import HTTPException, status, Request
from sqlalchemy import select, func, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from database.models.movies import (
    MoviesModel,
    CertificationsModel,
    StarsModel,
    DirectorModel,
    GenreModel,
    RatingModel
)
from database.models.order import OrderItemModel
from database.models.user import movie_likes, user_favorites
from schemas.movies import (
    MovieCreateRequestSchema,
    MovieUpdateRequestSchema,
    GenresListSchema,
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieReadSchema,
    MovieDetailBase,
    GenresReadSchema
)
from schemas.social import CommentsListSchema
from utils.service_helpers import pagination_helper


class MovieService:
    @staticmethod
    async def get_movies(
            request: Request,
            db: AsyncSession,
            filters: dict,
            page: int,
            per_page: int,
            sort_by: str,
            user_id: int
    ) -> MovieListResponseSchema:
        stmt = select(MoviesModel)
        if filters.get("only_favorites") and user_id:
            stmt = stmt.join(
                user_favorites,
                user_favorites.c.movie_id == MoviesModel.id
            ).where(user_favorites.c.user_id == user_id)
        if filters.get("star"):
            stmt = stmt.join(MoviesModel.stars).where(
                StarsModel.name.ilike(f"%{filters['star']}%"))
        if filters.get("director"):
            stmt = stmt.join(MoviesModel.directors).where(
                DirectorModel.name.ilike(f"%{filters['director']}%"))
        if filters.get("genre"):
            stmt = stmt.join(MoviesModel.genres).where(
                GenreModel.name.ilike(f"%{filters['genre']}%")
            )
        if filters.get("name"):
            stmt = stmt.where(MoviesModel.name.ilike(f"%{filters['name']}%"))
        if filters.get("description"):
            stmt = stmt.where(MoviesModel.description.ilike(
                f"%{filters['description']}%"
            ))
        if filters.get("min_year"):
            stmt = stmt.where(MoviesModel.year >= filters["min_year"])
        if filters.get("max_year"):
            stmt = stmt.where(MoviesModel.year <= filters["max_year"])
        if filters.get("min_rating"):
            stmt = stmt.where(MoviesModel.imdb >= filters["min_rating"])
        if filters.get("min_price"):
            stmt = stmt.where(MoviesModel.price >= filters["min_price"])
        if filters.get("max_price"):
            stmt = stmt.where(MoviesModel.price <= filters["max_price"])

        sort_options = {
            "newest": desc(MoviesModel.year),
            "oldest": asc(MoviesModel.year),
            "rating": desc(MoviesModel.imdb),
            "votes": desc(MoviesModel.votes),
            "price_asc": asc(MoviesModel.price),
            "price_desc": desc(MoviesModel.price),
        }

        stmt = stmt.order_by(
            sort_options.get(sort_by, desc(MoviesModel.year)))
        stmt = stmt.options(
            selectinload(MoviesModel.stars),
            selectinload(MoviesModel.certification),
            selectinload(MoviesModel.genres),
            selectinload(MoviesModel.directors)
        )

        result = await pagination_helper(
            request=request, db=db, stmt=stmt, page=page, per_page=per_page
        )
        return MovieListResponseSchema(
            items=[
                MovieListItemSchema.model_validate(movie)
                for movie in result["items"]
            ],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            prev_page=result["prev_page"],
            next_page=result["next_page"],
        )

    @staticmethod
    async def get_movie_by_id(
            movie_id: int,
            db: AsyncSession,
            user_id: int | None = None
    ) -> MoviesModel | None:
        stats_stmt = select(
            func.avg(RatingModel.score).label("average"),
            func.count(RatingModel.id).label("count")
        ).where(RatingModel.movie_id == movie_id)

        stats_result = await db.execute(stats_stmt)
        stats = stats_result.one()

        stmt_movie = (
            select(MoviesModel)
            .options(
                selectinload(MoviesModel.certification),
                selectinload(MoviesModel.genres),
                selectinload(MoviesModel.stars),
                selectinload(MoviesModel.directors),
                selectinload(MoviesModel.comments),
            )
            .where(MoviesModel.id == movie_id)
        )
        result = await db.execute(stmt_movie)
        movie = result.scalar_one_or_none()

        if movie is None:
            return None

        if user_id:
            like_check = await db.execute(
                select(movie_likes).where(
                    movie_likes.c.movie_id == movie_id,
                    movie_likes.c.user_id == user_id
                )
            )
            movie.is_liked_by_user = like_check.first() is not None
            in_favorites = await db.execute(
                select(user_favorites).where(
                    user_favorites.c.movie_id == movie_id,
                    user_favorites.c.user_id == user_id
                )
            )
            movie.is_favorited_by_user = in_favorites.first() is not None
        movie.average_rating = round(float(stats.average or 0.0), 1)
        movie.total_ratings = stats.count
        return movie

    @staticmethod
    async def entities_helper(
            entities: list,
            db_model: Type[StarsModel | DirectorModel | GenreModel],
            db: AsyncSession
    ) -> list:
        result = []
        for entity in entities:
            db_entity = await db.scalar(
                select(db_model).where(
                    func.lower(db_model.name) == entity.lower())
            )
            if db_entity is None:
                db_entity = db_model(name=entity)
                db.add(db_entity)
                await db.flush()
            result.append(db_entity)
        return result

    @staticmethod
    async def certification_helper(
            certification_name: str,
            db: AsyncSession
    ) -> CertificationsModel:
        certification = await db.scalar(
            select(CertificationsModel).where(
                func.lower(
                    CertificationsModel.name
                ) == certification_name.lower()
            )
        )
        if not certification:
            certification = CertificationsModel(name=certification_name)
            db.add(certification)
            await db.flush()
        return certification

    @staticmethod
    async def movie_create(
            movie_data: MovieCreateRequestSchema,
            db: AsyncSession
    ) -> MoviesModel:
        service = MovieService()
        db_movie = await db.scalar(select(MoviesModel).where(
            (MoviesModel.name == movie_data.name)
            & (MoviesModel.year == movie_data.year)
            & (MoviesModel.time == movie_data.time)
        ))
        if db_movie:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Movie already exists."
            )

        certification = await service.certification_helper(
            certification_name=movie_data.certification, db=db
        )

        genres = await service.entities_helper(movie_data.genres, GenreModel,
                                               db)
        stars = await service.entities_helper(movie_data.stars, StarsModel, db)
        directors = await service.entities_helper(
            movie_data.directors, DirectorModel, db
        )
        new_movie = MoviesModel(
            name=movie_data.name,
            uuid=uuid.uuid4(),
            year=movie_data.year,
            time=movie_data.time,
            imdb=movie_data.imdb,
            votes=movie_data.votes,
            meta_score=movie_data.meta_score,
            gross=movie_data.gross,
            description=movie_data.description,
            price=movie_data.price,
            certification=certification,
            stars=stars,
            directors=directors,
            genres=genres
        )
        db.add(new_movie)
        try:
            await db.commit()
            return await MovieService.get_movie_by_id(
                movie_id=new_movie.id, db=db
            )
        except SQLAlchemyError as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Something went wrong. Try again later. {e}"
            )


    @staticmethod
    async def movie_update(
            movie_id: int,
            movie_data: MovieUpdateRequestSchema,
            db: AsyncSession
    ) -> MovieReadSchema:
        service = MovieService()
        db_movie = await service.get_movie_by_id(movie_id=movie_id, db=db)
        if not db_movie:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not found."
            )
        update_data = movie_data.model_dump(exclude_unset=True)
        if "stars" in update_data:
            db_movie.stars = await service.entities_helper(
                update_data.pop("stars"), StarsModel, db
            )

        if "directors" in update_data:
            db_movie.directors = await service.entities_helper(
                update_data.pop("directors"), DirectorModel, db
            )

        if "genres" in update_data:
            db_movie.genres = await service.entities_helper(
                update_data.pop("genres"), GenreModel, db
            )

        if "certification" in update_data:
            cert_name = update_data.pop("certification")
            certification = await service.certification_helper(
                certification_name=cert_name, db=db
            )
            update_data["certification"] = certification

        for field, value in update_data.items():
            setattr(db_movie, field, value)

        try:
            await db.commit()
            updated_movie = await service.get_movie_by_id(
                movie_id=movie_id, db=db
            )
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something went wrong. Try again later."
            )
        for comment in updated_movie.comments:
            set_committed_value(comment, "replies", [])
        comments_data = CommentsListSchema(
            items=updated_movie.comments,
            total_items=len(updated_movie.comments),
            total_pages=1,
            prev_page=None,
            next_page=None
        )

        return MovieReadSchema(
            **MovieDetailBase.model_validate(updated_movie).model_dump(),
            comments=comments_data
        )

    @staticmethod
    async def movie_delete(movie_id: int, db: AsyncSession) -> None:
        ownership_stmt = select(func.count()).select_from(
            OrderItemModel).where(
            OrderItemModel.movie_id == movie_id
        )
        result = await db.execute(ownership_stmt)
        if result.scalar() > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete movie: it has been purchased by users."
            )

        db_movie = await MovieService.get_movie_by_id(movie_id=movie_id, db=db)
        if not db_movie:
            return None

        await db.delete(db_movie)
        await db.commit()
        return True

    @staticmethod
    async def get_genres_list(
            request: Request,
            db: AsyncSession,
            page: int,
            per_page: int,
            name: str | None
    ) -> GenresListSchema:
        stmt = (
            select(GenreModel,
                   func.count(MoviesModel.id).label("total_movies"))
            .outerjoin(GenreModel.movies)
            .group_by(GenreModel.id)
        )
        if name:
            stmt = stmt.where(GenreModel.name.ilike(f"%{name}%"))

        result = await pagination_helper(
            request=request, page=page, per_page=per_page,
            db=db, stmt=stmt, scalars=False
        )
        return GenresListSchema(
            items=[
                GenresReadSchema(
                    id=row[0].id,
                    name=row[0].name,
                    total_movies=row.total_movies
                )
                for row in result["items"]
            ],
            prev_page=result["prev_page"],
            next_page=result["next_page"],
            total_pages=result["total_pages"],
            total_items=result["total_items"],
        )

    @staticmethod
    async def rate_movie(
            db: AsyncSession,
            movie_id: int,
            user_id: int,
            score: int
    ) -> dict[str, str | int]:
        stmt = select(RatingModel).where(
            RatingModel.movie_id == movie_id,
            RatingModel.user_id == user_id
        )
        existing_rating = await db.scalar(stmt)

        if existing_rating:
            existing_rating.score = score
        else:
            new_rating = RatingModel(
                movie_id=movie_id,
                user_id=user_id,
                score=score
            )
            db.add(new_rating)

        await db.commit()

        stats_stmt = select(
            func.avg(RatingModel.score).label("average"),
            func.count(RatingModel.id).label("count")
        ).where(RatingModel.movie_id == movie_id)

        stats = await db.execute(stats_stmt)
        result = stats.one()

        return {
            "movie_id": movie_id,
            "user_score": score,
            "new_average": round(float(result.average), 1),
            "total_ratings": result.count
        }
