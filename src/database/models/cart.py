from sqlalchemy import Integer, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List
from database.models.base import Base

class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="cart"
    )
    items: Mapped[List["CartItemModel"]] = relationship(
        "CartItemModel",
        back_populates="cart",
        cascade="all, delete-orphan"
    )

class CartItemModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cart_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    cart: Mapped["CartModel"] = relationship(
        "CartModel",
        back_populates="items"
    )
    movie: Mapped["MoviesModel"] = relationship("MoviesModel")

    __table_args__ = (
        UniqueConstraint(
            "cart_id", "movie_id", name="unique_cart_movie"
        ),
    )
