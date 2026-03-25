from fastapi import HTTPException, status, Request
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models.cart import CartModel, CartItemModel
from database.models.order import (
    OrderModel,
    OrderItemModel,
    OrderStatus,
    OrderItemStatus
)
from database.models.user import UserGroupEnum, UserModel
from schemas.order import OrderListSchema, OrderListItemSchema
from utils.service_helpers import pagination_helper


class OrderService:
    @staticmethod
    async def place_order(db: AsyncSession, user_id: int):
        cart_stmt = (
            select(CartModel)
            .where(CartModel.user_id == user_id)
            .options(
                selectinload(CartModel.items).joinedload(CartItemModel.movie))
        )
        cart = await db.scalar(cart_stmt)

        if not cart or not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your cart is empty."
            )

        total_amount = sum(item.movie.price for item in cart.items)
        new_order = OrderModel(
            user_id=user_id,
            total_amount=total_amount,
            status=OrderStatus.PENDING,
        )
        db.add(new_order)
        await db.flush()

        for cart_item in cart.items:
            order_item = OrderItemModel(
                order_id=new_order.id,
                movie_id=cart_item.movie_id,
                price_paid=cart_item.movie.price
            )
            db.add(order_item)

        await db.execute(
            delete(CartItemModel).where(CartItemModel.cart_id == cart.id))
        await db.commit()

        final_order_stmt = (
            select(OrderModel)
            .where(OrderModel.id == new_order.id)
            .options(
                selectinload(OrderModel.items)
                .joinedload(OrderItemModel.movie)
            )
        )
        result = await db.execute(final_order_stmt)
        return result.scalar_one()

    @staticmethod
    async def get_order_history(
            request: Request,
            page: int,
            per_page: int,
            db: AsyncSession,
            user: UserModel
    ):

        stmt = select(OrderModel)
        if user.group != UserGroupEnum.ADMIN:
            stmt = stmt.where(OrderModel.user_id == user.id)

        stmt = stmt.options(
            selectinload(OrderModel.items)
            .selectinload(OrderItemModel.movie)
        ).order_by(OrderModel.created_at.desc())

        result = await pagination_helper(
            request=request, db=db, stmt=stmt, page=page, per_page=per_page
        )
        return OrderListSchema(
            items=[
                OrderListItemSchema.model_validate(order)
                for order in result["items"]
            ],
            total_items=result["total_items"],
            total_pages=result["total_pages"],
            next_page=result["next_page"],
            prev_page=result["prev_page"]
        )

    @staticmethod
    async def get_order_details(db: AsyncSession, user: UserModel, order_id: int):
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == order_id)
            .options(
                selectinload(OrderModel.items).joinedload(OrderItemModel.movie)
            )
        )
        if user.group != UserGroupEnum.ADMIN:
            stmt = stmt.where(
                OrderModel.user_id == user.id
            )

        order = await db.scalar(stmt)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found."
            )
        return order

    @staticmethod
    async def cancel_order(db: AsyncSession, user_id: int, order_id: int):
        stmt = (
            select(OrderModel)
            .where(
                OrderModel.id == order_id,
                OrderModel.user_id == user_id
            )
            .options(
                selectinload(OrderModel.items).joinedload(OrderItemModel.movie)
            )
        )
        order = await db.scalar(stmt)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found."
            )

        for item in order.items:
            item.status = OrderItemStatus.CANCELED
        order.status = OrderStatus.CANCELED

        await db.commit()
        return order
