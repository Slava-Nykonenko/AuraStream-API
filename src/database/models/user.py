import enum
from datetime import datetime, date, UTC
from typing import List, Optional

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    Table,
    Text,
    Date,
    Column,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref

from database.models.base import Base


user_favorites = Table(
    "user_favorites",
    Base.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "movie_id",
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "added_at",
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now()
    )
)

movie_likes = Table(
    "movie_likes",
    Base.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "movie_id",
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column("created_at", DateTime, default=func.now())
)


class UserGroupEnum(str, enum.Enum):
    USER = "USER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


class GenderEnum(str, enum.Enum):
    MAN = "MAN"
    WOMAN = "WOMAN"


class UserGroupModel(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[UserGroupEnum] = mapped_column(
        Enum(UserGroupEnum),
        unique=True,
        nullable=False,
        default=UserGroupEnum.USER
    )

    users: Mapped[List["UserModel"]] = relationship(
        "UserModel", back_populates="group"
    )


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user_groups.id"),
        nullable=False
    )

    group: Mapped["UserGroupModel"] = relationship(
        "UserGroupModel",
        back_populates="users")
    profile: Mapped[Optional["UserProfileModel"]] = relationship(
        "UserProfileModel",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    favorite_movies: Mapped[List["MoviesModel"]] = relationship(
        "MoviesModel",
        secondary=user_favorites,
        backref="favorited_by"
    )
    liked_movies: Mapped[List["MoviesModel"]] = relationship(
        "MoviesModel",
        secondary=movie_likes,
        backref="liked_by"
    )
    comments: Mapped[List["CommentModel"]] = relationship(
        "CommentModel",
        back_populates="user"
    )

    activation_tokens: Mapped[List["ActivationTokenModel"]] = relationship(
        "ActivationTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[
        List["PasswordResetTokenModel"]] = relationship(
        "PasswordResetTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshTokenModel"]] = relationship(
        "RefreshTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    ratings: Mapped[List["RatingModel"]] = relationship(
        "RatingModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True
    )

    first_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    avatar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gender: Mapped[Optional[GenderEnum]] = mapped_column(
        Enum(GenderEnum),
        nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="profile"
    )


class TokenModelMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ActivationTokenModel(TokenModelMixin, Base):
    __tablename__ = "activation_tokens"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="activation_tokens"
    )


class RefreshTokenModel(TokenModelMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="refresh_tokens"
    )


class PasswordResetTokenModel(TokenModelMixin, Base):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="password_reset_tokens"
    )


class CommentModel(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="comments"
    )
    movie: Mapped["MoviesModel"] = relationship(
        "MoviesModel", back_populates="comments"
    )
    replies: Mapped[List["CommentModel"]] = relationship(
        "CommentModel",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan"
    )
