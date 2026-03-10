import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class UserBase(BaseModel):
    email: EmailStr


class PasswordBaseMixin:
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number.")
        if not re.search(r"[A-Z]", v):
            raise ValueError(
                "Password must contain at least one uppercase letter.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError(
                "Password must contain at least one special character.")
        return v


class UserCreateRequest(PasswordBaseMixin, UserBase):
    pass


class UserProfileRead(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    info: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginSchema(UserBase):
    password: str


class PasswordResetCompleteSchema(PasswordBaseMixin, BaseModel):
    token: str


class UserRead(UserBase):
    id: int
    is_active: bool
    group_id: int
    created_at: datetime

    profile: Optional[UserProfileRead] = None

    model_config = ConfigDict(from_attributes=True)


class MessageSchema(BaseModel):
    message: str

    model_config = ConfigDict(from_attributes=True)
