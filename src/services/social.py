from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from database.models.user import user_favorites, CommentModel
from schemas.social import CommentsListSchema, CommentReadSchema
from services.movies import generate_page_link


class SocialService:
    @staticmethod
    async def toggle_favorite(db: AsyncSession, user_id: int, movie_id: int):
        stmt = select(user_favorites).where(
            user_favorites.c.user_id == user_id,
            user_favorites.c.movie_id == movie_id
        )
        result = await db.execute(stmt)

        if result.first():
            await db.execute(delete(user_favorites).where(
                user_favorites.c.user_id == user_id,
                user_favorites.c.movie_id == movie_id
            ))
            return "removed"

        await db.execute(
            user_favorites.insert().values(user_id=user_id, movie_id=movie_id))
        return "added"

    @staticmethod
    async def add_comment(
            db: AsyncSession,
            user_id: int,
            movie_id: int,
            content: str
    ):
        new_comment = CommentModel(
            user_id=user_id, movie_id=movie_id, content=content
        )
        db.add(new_comment)
        await db.flush()
        return new_comment


class CommentService:
    @staticmethod
    async def get_movie_comments(
            db: AsyncSession,
            movie_id: int,
            page: int,
            per_page: int,
            request: Request = None
    ) -> CommentsListSchema:
        offset = (page - 1) * per_page

        stmt = (
            select(CommentModel)
            .where(CommentModel.movie_id == movie_id)
            .options(selectinload(CommentModel.user))
            .order_by(CommentModel.created_at.desc())
        )

        count_stmt = (
            select(func.count())
            .select_from(CommentModel)
            .where(CommentModel.movie_id == movie_id)
        )
        total_items = (await db.execute(count_stmt)).scalar() or 0
        total_pages = (total_items + per_page - 1) // per_page

        result = await db.execute(stmt.offset(offset).limit(per_page))
        comments_objs = result.scalars().all()

        comments_list = [
            CommentReadSchema.model_validate(comment)
            for comment in comments_objs
        ]

        return CommentsListSchema(
            items=comments_list,
            total_items=total_items,
            total_pages=total_pages,
            prev_page=await generate_page_link(
                request=request, page_number=page - 1, per_page=per_page
            ) if page > 1 and request else None,
            next_page=await generate_page_link(
                request=request, page_number=page + 1, per_page=per_page
            ) if page < total_pages and request else None,
        )
