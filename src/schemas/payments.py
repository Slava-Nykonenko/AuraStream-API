from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


class PaymentItemReadSchema(BaseModel):
    id: int
    order_item_id: int
    price_at_payment: Decimal

    model_config = ConfigDict(from_attributes=True)


class PaymentReadSchema(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    status: str
    created_at: datetime
    external_payment_id: Optional[str]
    items: List[PaymentItemReadSchema] = []

    model_config = ConfigDict(from_attributes=True)


class PaymentListSchema(BaseModel):
    items: List[PaymentReadSchema]
    total_items: int
    total_pages: int
    next_page: Optional[str]
    prev_page: Optional[str]


class CheckoutRequestSchema(BaseModel):
    order_id: int
    item_ids: Optional[List[int]] = Field(None)

