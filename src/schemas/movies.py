from decimal import Decimal
from typing import List, Optional
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, computed_field


class PaginatedResponseMixin(BaseModel):
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int
    total_items: int


class CertificationsSchema(BaseModel):
    name: str


class CertificationsReadSchema(CertificationsSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)


class GenresSchema(BaseModel):
    name: str


class GenresListItemSchema(GenresSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)


class GenresReadSchema(GenresListItemSchema):
    id: int
    total_movies: int

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def movies(self) -> str:
        safe_name = quote(self.name)
        return f"/movie_theater/movies?genre={safe_name}"


class GenresListSchema(PaginatedResponseMixin):
    genres: List[GenresReadSchema]


class StarsSchema(BaseModel):
    name: str


class StarsReadSchema(StarsSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)


class DirectorsSchema(BaseModel):
    name: str


class DirectorsReadSchema(DirectorsSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)


class MovieBaseSchema(BaseModel):
    name: str
    year: int
    time: int
    imdb: float
    description: str


class MovieListItemSchema(MovieBaseSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)


class MovieListResponseSchema(PaginatedResponseMixin):
    movies: List[MovieListItemSchema]

    model_config = ConfigDict(from_attributes=True)


class MovieReadSchema(MovieBaseSchema):
    id: int
    votes: int
    meta_score: float
    gross: float
    price: Decimal
    certification: CertificationsReadSchema
    stars: List[StarsReadSchema]
    directors: List[DirectorsReadSchema]
    genres: List[GenresListItemSchema]

    model_config = ConfigDict(from_attributes=True)


class MovieCreateRequestSchema(MovieBaseSchema):
    votes: int
    meta_score: float
    gross: float
    price: Decimal
    certification: str
    genres: List[str]
    stars: List[str]
    directors: List[str]


class MovieUpdateRequestSchema(BaseModel):
    name: Optional[str] = None
    year: Optional[int] = None
    time: Optional[int] = None
    imdb: Optional[float] = None
    description: Optional[str] = None
    votes: Optional[int] = None
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    price: Optional[Decimal] = None
    certification: Optional[str] = None
    genres: Optional[List[str]] = None
    stars: Optional[List[str]] = None
    directors: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class MovieFilterParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=50)

    name: Optional[str] = Field(None, description="Search by movie title")
    description: Optional[str] = Field(
        None, description="Search in movie synopsis"
    )
    star: Optional[str] = Field(None, description="Search by actor name")
    director: Optional[str] = Field(
        None, description="Search by director name"
    )
    genre: Optional[str] = Field(None, description="Search by movie genre")

    sort_by: str = Field(
        "newest",
        pattern="^(newest|oldest|rating|votes|price_asc|price_desc)$",
        description="Options: newest, oldest, rating, votes, price_asc, price_desc"
    )

    min_year: Optional[int] = Field(None, ge=1888, le=2100)
    max_year: Optional[int] = Field(None, ge=1888, le=2100)
    min_rating: Optional[float] = Field(None, ge=0, le=10)
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
