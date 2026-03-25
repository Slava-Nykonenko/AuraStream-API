from typing import List

from fastapi import HTTPException, status, Request
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.orm.attributes import set_committed_value

from core.settings import settings
from database.models.user import (
    user_favorites,
    CommentModel,
    UserModel,
    UserProfileModel
)
from schemas.social import (
    CommentsListSchema,
    CommentReadSchema,
    ReplyCreateSchema,
    UserProfileCreateSchema,
    UserProfileListItemSchema,
    UserProfilesListSchema
)
from tasks.email_tasks import send_email
from utils.service_helpers import pagination_helper

BASE_URL = settings.BASE_URL + "/movies"


class SocialService:
    @staticmethod
    async def toggle_favorite(
            db: AsyncSession, user_id: int, movie_id: int
    ) -> str:
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
            return "removed from"

        await db.execute(
            user_favorites.insert().values(user_id=user_id, movie_id=movie_id))
        return "added to"

    @staticmethod
    async def add_comment(
            db: AsyncSession,
            user_id: int,
            movie_id: int,
            content: str
    ) -> CommentModel:
        new_comment = CommentModel(
            user_id=user_id, movie_id=movie_id, content=content, replies=[]
        )
        db.add(new_comment)
        await db.flush()
        return new_comment

    @staticmethod
    async def create_reply(
            db: AsyncSession,
            movie_id: int,
            user: UserModel,
            reply_data: ReplyCreateSchema
    ) -> CommentModel:
        parent_stmt = (
            select(CommentModel)
            .options(
                joinedload(CommentModel.user).joinedload(UserModel.profile),
                joinedload(CommentModel.movie)
            )
            .where(
                CommentModel.id == reply_data.parent_id,
                CommentModel.movie_id == movie_id
            )
        )
        parent_result = await db.execute(parent_stmt)
        parent_comment = parent_result.scalar_one_or_none()

        if not parent_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found for this movie."
            )

        new_reply = CommentModel(
            content=reply_data.content,
            user_id=user.id,
            movie_id=movie_id,
            parent_id=reply_data.parent_id,
            replies=[]
        )

        db.add(new_reply)
        await db.commit()

        refresh_stmt = (
            select(CommentModel)
            .options(
                joinedload(CommentModel.user).joinedload(UserModel.profile))
            .where(CommentModel.id == new_reply.id)
        )
        new_reply_loaded = (await db.execute(refresh_stmt)).scalar_one()

        def get_full_name(user_obj: UserModel) -> str:
            profile = user_obj.profile
            first = profile.first_name or ""
            last = profile.last_name or ""
            return f"{first} {last}".strip() or "A user"

        body_data = {
            "user_name": get_full_name(parent_comment.user),
            "replier_name": get_full_name(user),
            "movie_name": parent_comment.movie.name,
            "message": f"{new_reply.content[:25]}..." if len(
                new_reply.content) > 25 else new_reply.content,
            "comment_url": f"{BASE_URL}/{movie_id}/comments/{reply_data.parent_id}"
        }

        send_email.delay(
            email=parent_comment.user.email,
            body_data=body_data,
            msg_type="reply",
        )

        return new_reply_loaded

    @staticmethod
    async def get_movie_comments(
            db: AsyncSession,
            movie_id: int,
            page: int,
            per_page: int,
            request: Request = None
    ) -> CommentsListSchema:
        stmt = (
            select(CommentModel)
            .where(
                CommentModel.movie_id == movie_id,
                CommentModel.parent_id == None
            )
            .options(
                selectinload(CommentModel.user).selectinload(
                    UserModel.profile),
                selectinload(CommentModel.replies)
            )
            .order_by(CommentModel.created_at.desc())
        )

        result = await pagination_helper(
            request=request, page=page, per_page=per_page, db=db, stmt=stmt
        )

        for comment in result["items"]:
            for reply in comment.replies:
                set_committed_value(reply, "replies", [])

        comments_list = [
            CommentReadSchema.model_validate(comment)
            for comment in result["items"]
        ]

        return CommentsListSchema(
            items=comments_list,
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            prev_page=result["prev_page"],
            next_page=result["next_page"],
        )

    @staticmethod
    async def get_comment_replies(
            request: Request,
            db: AsyncSession,
            comment_id: int,
            page: int = 1,
            per_page: int = 10
    ) -> List[CommentReadSchema]:
        stmt = (
            select(CommentModel)
            .where(CommentModel.parent_id == comment_id)
            .options(
                selectinload(CommentModel.user))
            .order_by(
                CommentModel.created_at.desc())
        )
        result = await pagination_helper(
            request=request, page=page, per_page=per_page, db=db, stmt=stmt
        )
        return [CommentReadSchema.model_validate(r) for r in result["items"]]

    @staticmethod
    async def list_profiles(
            request: Request,
            db: AsyncSession,
            page: int,
            per_page: int,
    ):
        stmt = select(UserProfileModel).order_by(UserProfileModel.id.asc())
        result = await pagination_helper(
            request=request, db=db, stmt=stmt, page=page, per_page=per_page
        )

        return UserProfilesListSchema(
            items=[UserProfileListItemSchema.model_validate(p) for p in
                   result["items"]],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            prev_page=result["prev_page"],
            next_page=result["next_page"]
        )


    @staticmethod
    async def profile_retrieve(
            profile_id: int,
            db: AsyncSession,
    ) -> UserProfileModel:
        return await db.scalar(
            select(UserProfileModel).where(UserProfileModel.id == profile_id)
        )

    @staticmethod
    async def create_user_profile(
            db: AsyncSession,
            user: UserModel,
            profile_data: UserProfileCreateSchema
    ) -> UserProfileModel:
        existing_profile = await db.scalar(
            select(UserProfileModel).where(UserProfileModel.user_id == user.id)
        )

        if existing_profile:
            raise HTTPException(
                status_code=400,
                detail="You already have a profile."
            )

        data = profile_data.model_dump(exclude={"user_id"})
        new_profile = UserProfileModel(
            user_id=user.id,
            **data
        )

        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)
        return new_profile
