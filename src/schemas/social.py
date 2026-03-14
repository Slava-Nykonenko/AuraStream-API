import re
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, field_validator, Field
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
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    info: Optional[str] = Field(None, max_length=1000)

    gender: Optional[GenderEnum] = None
    date_of_birth: Optional[date] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_and_capitalize(cls, value: str):
        if value:
            return value.strip().capitalize()
        return value

    @field_validator("avatar")
    @classmethod
    def validate_avatar_url(cls, value: Optional[str]):
        if value and not re.match(r'^https?://.*\.(jpg|jpeg|png|gif|webp)$', value):
            raise ValueError("Avatar must be a valid image URL.")
        return value

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, value: date):
        today = date.today()
        age = today.year - value.year - (
                    (today.month, today.day) < (value.month, value.day))
        if age < 16:
            raise ValueError("User must be at least 16 years old.")
        return value


class UserProfileReadSchema(UserProfileCreateSchema):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class UserProfileListItemSchema(UserProfileBaseSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UserProfilesListSchema(PaginatedResponse[UserProfileListItemSchema]):
    model_config = ConfigDict(from_attributes=True)
