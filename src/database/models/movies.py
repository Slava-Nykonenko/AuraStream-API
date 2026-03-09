from decimal import Decimal

from sqlalchemy import (
    Integer,
    UUID,
    String,
    Float,
    DECIMAL,
    ForeignKey,
    Table,
    Column
)
from sqlalchemy.orm import mapped_column, Mapped, relationship

from database.models.base import Base


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
