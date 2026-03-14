from sqlalchemy import Integer, ForeignKey, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List
from database.models.base import Base


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="completed")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="orders"
    )
    items: Mapped[List["OrderItemModel"]] = relationship(
        "OrderItemModel",
        back_populates="order",
        cascade="all, delete-orphan"
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("movies.id", ondelete="RESTRICT"),
        nullable=False
    )

    price_paid: Mapped[float] = mapped_column(Float, nullable=False)

    order: Mapped["OrderModel"] = relationship(
        "OrderModel", back_populates="items"
    )
    movie: Mapped["MoviesModel"] = relationship("MoviesModel")
