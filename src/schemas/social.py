from pydantic import BaseModel, ConfigDict
from datetime import datetime

from schemas.base import PaginatedResponse


class CommentCreateSchema(BaseModel):
    content: str


class CommentReadSchema(BaseModel):
    id: int
    content: str
    created_at: datetime
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class SocialActionResponseSchema(BaseModel):
    status: str
    message: str


class CommentsListSchema(PaginatedResponse[CommentReadSchema]):
    pass
