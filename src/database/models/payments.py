import enum
from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import (
    Integer,
    ForeignKey,
    DateTime,
    func,
    String,
    Numeric,
    Enum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class PaymentStatus(str, enum.Enum):
    SUCCESSFUL = "SUCCESSFUL"
    CANCELED = "CANCELED"
    REFUNDED = "REFUNDED"


class PaymentsModel(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        default=PaymentStatus.SUCCESSFUL,
        nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )
    external_payment_id: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="payments"
    )
    order: Mapped["OrderModel"] = relationship(
        "OrderModel",
        back_populates="payments"
    )
    payment_items: Mapped[List["PaymentItems"]] = relationship(
        "PaymentItems",
        back_populates="payment"
    )


class PaymentItems(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False
    )
    order_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False
    )
    price_at_payment: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    payment: Mapped[PaymentsModel] = relationship(
        "PaymentsModel",
        back_populates="payment_items"
    )
    order_item: Mapped["OrderItemModel"] = relationship(
        "OrderItemModel",
        back_populates="payment_items"
    )
