from typing import Optional, List

from pydantic import BaseModel, ConfigDict
from datetime import datetime, date

from database.models.user import GenderEnum
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


class UserProfileBaseSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None


class UserProfileCreateSchema(UserProfileBaseSchema):
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    info: Optional[str] = None


class UserProfileReadSchema(UserProfileCreateSchema):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class UserProfileListItemSchema(UserProfileBaseSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UserProfilesListSchema(PaginatedResponse[UserProfileListItemSchema]):
    model_config = ConfigDict(from_attributes=True)
