from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict

from schemas.base import PaginatedResponse
from schemas.movies import MovieListItemSchema


class OrderBaseSchema(BaseModel):
    total_amount: float
    status: str
    created_at: datetime


class OrderListItemSchema(OrderBaseSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)


class OrderListSchema(PaginatedResponse[OrderListItemSchema]):
    model_config = ConfigDict(from_attributes=True)


class OrderDetailSchema(OrderListItemSchema):
    items: List[MovieListItemSchema]
