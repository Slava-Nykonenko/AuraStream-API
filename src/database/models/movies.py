from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import (
    Integer,
    UUID,
    String,
    Float,
    DECIMAL,
    ForeignKey,
    Table,
    Column,
    select,
    func,
    UniqueConstraint,
    CheckConstraint,
    DateTime
)
from sqlalchemy.orm import mapped_column, Mapped, relationship, column_property

from database.models.base import Base
from database.models.user import movie_likes, UserModel

MoviesStarsModel = Table(
    "movies_stars",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "star_id",
        ForeignKey("stars.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )
)

MoviesGenresModel = Table(
    "movies_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )
)

MoviesDirectorModel = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "director_id",
        ForeignKey("directors.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    )
)


class NameIdMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class CertificationsModel(NameIdMixin, Base):
    __tablename__ = "certifications"

    movies: Mapped[list["MoviesModel"]] = relationship(
        "MoviesModel",
        back_populates="certification"
    )

    def __repr__(self):
        return f"<Certificate (name: {self.name})>"


class MoviesModel(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[UUID] = mapped_column(UUID, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meta_score: Mapped[float] = mapped_column(Float, nullable=True, default=0)
    gross: Mapped[float] = mapped_column(Float, nullable=True, default=0)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL, nullable=True, default=0)
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="CASCADE"),
        nullable=False
    )

    certification: Mapped[CertificationsModel] = relationship(
        CertificationsModel,
        back_populates="movies"
    )
    stars: Mapped[list["StarsModel"]] = relationship(
        "StarsModel",
        secondary=MoviesStarsModel,
        back_populates="movies"
    )
    directors: Mapped[list["DirectorModel"]] = relationship(
        "DirectorModel",
        secondary=MoviesDirectorModel,
        back_populates="movies"
    )
    genres: Mapped[list["GenreModel"]] = relationship(
        "GenreModel",
        secondary=MoviesGenresModel,
        back_populates="movies"
    )

    likes: Mapped[list["UserModel"]] = relationship(
        "UserModel",
        secondary=movie_likes,
        back_populates="liked_movies",
        viewonly=True
    )

    likes_count: Mapped[int] = column_property(
        select(func.count(movie_likes.c.user_id))
        .where(movie_likes.c.movie_id == id)
        .correlate_except(movie_likes)
        .scalar_subquery()
    )
    ratings: Mapped[List["RatingModel"]] = relationship(
        "RatingModel",
        back_populates="movie",
        cascade="all, delete-orphan"
    )
    in_carts: Mapped[List["CartItemModel"]] = relationship(
        "CartItemModel",
        back_populates="movie"
    )
    comments = relationship("CommentModel", back_populates="movie")


class StarsModel(NameIdMixin, Base):
    __tablename__ = "stars"

    movies: Mapped[list["MoviesModel"]] = relationship(
        "MoviesModel",
        secondary=MoviesStarsModel,
        back_populates="stars"
    )

    def __repr__(self):
        return f"<Star (name: {self.name})>"


class GenreModel(NameIdMixin, Base):
    __tablename__ = "genres"

    movies: Mapped[list["MoviesModel"]] = relationship(
        "MoviesModel",
        secondary=MoviesGenresModel,
        back_populates="genres"
    )

    def __repr__(self):
        return f"<Genre (name: {self.name})>"


class DirectorModel(NameIdMixin, Base):
    __tablename__ = "directors"

    movies: Mapped[list["MoviesModel"]] = relationship(
        "MoviesModel",
        secondary=MoviesDirectorModel,
        back_populates="directors"
    )

    def __repr__(self):
        return f"<Director (name: {self.name})>"


class RatingModel(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False
    )

    score: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="ratings"
    )
    movie: Mapped["MoviesModel"] = relationship(
        "MoviesModel", back_populates="ratings"
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "movie_id",
            name="unique_user_movie_rating"
        ),
        CheckConstraint(
            "score >= 0 AND score <= 10",
            name="check_score_range"
        ),
    )
