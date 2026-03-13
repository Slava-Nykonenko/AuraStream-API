import uuid
from typing import Type

from fastapi import HTTPException, status, Request
from sqlalchemy import select, func, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models.movies import (
    MoviesModel,
    CertificationsModel,
    StarsModel,
    DirectorModel,
    GenreModel
)
from database.models.user import movie_likes, user_favorites, CommentModel
from schemas.movies import (
    MovieCreateRequestSchema,
    MovieUpdateRequestSchema,
    GenresListSchema,
    GenresReadSchema
)


async def generate_page_link(
        request: Request,
        page_number: int,
        per_page: int
):
    params = dict(request.query_params)
    params["page"] = page_number
    params["per_page"] = per_page

    from urllib.parse import urlencode
    print(f"{request.url.path}?{urlencode(params)}")
    return f"{request.url.path}?{urlencode(params)}"


class MovieService:
    @staticmethod
    async def get_movies(
            db: AsyncSession,
            filters: dict,
            page: int,
            per_page: int,
            sort_by: str,
            user_id: int
    ):
        offset = (page - 1) * per_page
        stmt = select(MoviesModel)
        if filters.get("only_favorites") and user_id:
            stmt = stmt.join(
                user_favorites, user_favorites.c.movie_id == MoviesModel.id
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

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items = (await db.execute(count_stmt)).scalar() or 0

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
        ).offset(offset).limit(per_page)

        result = await db.execute(stmt)
        return result.scalars().all(), total_items

    @staticmethod
    async def get_movie_by_id(
            movie_id: int,
            db: AsyncSession,
            user_id: int | None = None
    ) -> MoviesModel:
        stmt_movie = (
            select(MoviesModel)
            .options(
                selectinload(MoviesModel.certification),
                selectinload(MoviesModel.genres),
                selectinload(MoviesModel.stars),
                selectinload(MoviesModel.directors),
                selectinload(MoviesModel.comments)
            )
            .where(MoviesModel.id == movie_id)
        )
        result = await db.execute(stmt_movie)
        movie = result.scalar_one_or_none()

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
        return movie

    @staticmethod
    def generate_page_link(request: Request, page_number: int, per_page: int):
        params = dict(request.query_params)
        params["page"] = page_number
        params["per_page"] = per_page

        from urllib.parse import urlencode
        return f"{request.url.path}?{urlencode(params)}"

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
                    CertificationsModel.name) == certification_name.lower()
            )
        )
        if not certification:
            certification = CertificationsModel(name=certification_name)
            db.add(certification)
            await db.flush()
        return certification

    async def movie_create(
            self,
            movie_data: MovieCreateRequestSchema,
            db: AsyncSession
    ):
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

        certification = await self.certification_helper(
            certification_name=movie_data.certification, db=db
        )

        genres = await self.entities_helper(movie_data.genres, GenreModel, db)
        stars = await self.entities_helper(movie_data.stars, StarsModel, db)
        directors = await self.entities_helper(movie_data.directors,
                                               DirectorModel, db)
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
            await db.refresh(
                new_movie,
                ["certification", "stars", "directors", "genres"]
            )
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something went wrong. Try again later."
            )
        return new_movie

    async def movie_update(
            self,
            movie_id: int,
            movie_data: MovieUpdateRequestSchema,
            db: AsyncSession
    ):
        db_movie = await self.get_movie_by_id(movie_id=movie_id, db=db)
        if not db_movie:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not found."
            )
        update_data = movie_data.model_dump(exclude_unset=True)
        if "stars" in update_data:
            db_movie.stars = await self.entities_helper(
                update_data.pop("stars"), StarsModel, db
            )

        if "directors" in update_data:
            db_movie.directors = await self.entities_helper(
                update_data.pop("directors"), DirectorModel, db
            )

        if "genres" in update_data:
            db_movie.genres = await self.entities_helper(
                update_data.pop("genres"), GenreModel, db
            )

        if "certification" in update_data:
            cert_name = update_data.pop("certification")
            certification = await self.certification_helper(
                certification_name=cert_name, db=db
            )
            update_data["certification"] = certification

        for field, value in update_data.items():
            setattr(db_movie, field, value)

        try:
            await db.commit()
            await db.refresh(db_movie)
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something went wrong. Try again later."
            )

        return db_movie

    async def movie_delete(self, movie_id: int, db: AsyncSession):
        db_movie = await self.get_movie_by_id(movie_id=movie_id, db=db)
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
    ):
        offset = (page - 1) * per_page
        stmt = (
            select(GenreModel,
                   func.count(MoviesModel.id).label("total_movies"))
            .outerjoin(GenreModel.movies)
            .group_by(GenreModel.id)
        )
        if name:
            stmt = stmt.where(GenreModel.name.ilike(f"%{name}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items = (await db.execute(count_stmt)).scalar() or 0
        total_pages = (total_items + per_page - 1) // per_page

        result = await db.execute(stmt.offset(offset).limit(per_page))
        genres_list = []
        for genre_obj, count in result.all():
            genre_obj.total_movies = count
            genres_list.append(GenresReadSchema.model_validate(genre_obj))

        response = GenresListSchema(
            items=genres_list,
            prev_page=generate_page_link(
                request=request, page_number=page - 1, per_page=per_page
            ) if page > 1 else None,
            next_page=generate_page_link(
                request=request, page_number=page + 1, per_page=per_page
            ) if page < total_pages else None,
            total_pages=total_pages,
            total_items=total_items,
        )
        return response
