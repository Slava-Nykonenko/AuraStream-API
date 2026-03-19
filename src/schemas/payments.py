from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from database.models.payments import PaymentStatus
from schemas.base import PaginatedResponse
from schemas.order import OrderDetailSchema
from schemas.user import UserRead


class PaymentItemReadSchema(BaseModel):
    id: int
    order_item_id: int
    price_at_payment: Decimal

    model_config = ConfigDict(from_attributes=True)


class PaymentBaseSchema(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    status: str

    model_config = ConfigDict(from_attributes=True)


class PaymentReadSchema(BaseModel):
    created_at: datetime
    external_payment_id: Optional[str]
    items: List[PaymentItemReadSchema] = []


class PaymentListSchema(PaginatedResponse, BaseModel):
    items: List[PaymentReadSchema]


class CheckoutRequestSchema(BaseModel):
    order_id: int
    item_ids: Optional[List[int]] = Field(None)


class RefundRequestSchema(BaseModel):
    payment_id: int


class PaymentAdminListItemSchema(PaymentBaseSchema):
    user_id: int


class PaymentAdminListSchema(PaginatedResponse, BaseModel):
    items: List[PaymentAdminListItemSchema]


class PaymentAdminReadSchema(PaymentReadSchema):
    user_id: int
    user: UserRead
    order: OrderDetailSchema

    model_config = ConfigDict(from_attributes=True)


class AdminPaymentFilterSchema(BaseModel):
    user_id: Optional[int] = Field(
        None, description="Filter by specific User ID"
    )
    status: Optional[PaymentStatus] = Field(
        None,
        description="Filter by payment status (e.g., SUCCESSFUL, REFUNDED)"
    )
    date_from: Optional[datetime] = Field(
        None, description="Start date for filtering (inclusive)"
    )
    date_to: Optional[datetime] = Field(
        None, description="End date for filtering (inclusive)"
    )
    external_payment_id: Optional[str] = Field(
        None, description="Search by Stripe Session/Intent ID"
    )

    model_config = ConfigDict(from_attributes=True)
