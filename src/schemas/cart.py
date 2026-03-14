from typing import List

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class CartItemCreateSchema(BaseModel):
    movie_id: int


class CartItemReadSchema(BaseModel):
    id: int
    movie_id: int
    movie_name: str
    added_at: datetime
    price_at_addition: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class CartReadSchema(BaseModel):
    id: int
    user_id: int
    items: List[CartItemReadSchema]
    total_items: int
    total_price: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class CartActionResponseSchema(BaseModel):
    status: str
    message: str
    item_count: int
