from typing import Optional, List

from pydantic import BaseModel, ConfigDict
from datetime import datetime

from schemas.base import PaginatedResponse


class CommentCreateSchema(BaseModel):
    content: str


class ReplyCreateSchema(BaseModel):
    content: str
    parent_id: int


class CommentReadSchema(BaseModel):
    id: int
    content: str
    created_at: datetime
    user_id: int
    parent_id: Optional[int] = None
    replies: List["CommentReadSchema"] = []
    likes_num: int = 0

    model_config = ConfigDict(from_attributes=True)


class SocialActionResponseSchema(BaseModel):
    status: str
    message: str


class CommentsListSchema(PaginatedResponse[CommentReadSchema]):
    pass
