from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models.order import OrderItemModel, OrderModel
from database.models.cart import CartModel, CartItemModel
from database.models.movies import MoviesModel
from schemas.cart import CartItemCreateSchema


class CartService:
    @staticmethod
    async def get_or_create_cart(db: AsyncSession, user_id: int) -> CartModel:
        stmt = (
            select(CartModel)
            .where(CartModel.user_id == user_id)
            .options(selectinload(CartModel.items))
        )
        cart = await db.scalar(stmt)
        if not cart:
            cart = CartModel(user_id=user_id)
            db.add(cart)
            await db.flush()
        return cart

    @staticmethod
    async def add_item(
            db: AsyncSession,
            user_id: int,
            payload: CartItemCreateSchema
    ):
        movie = await db.get(MoviesModel, payload.movie_id)
        if not movie:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie not found."
            )

        ownership_stmt = select(OrderItemModel).join(OrderModel).where(
            OrderModel.user_id == user_id,
            OrderItemModel.movie_id == payload.movie_id
        )
        ownership_check = await db.execute(ownership_stmt)
        if ownership_check.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already own this movie."
            )

        cart = await CartService.get_or_create_cart(db, user_id)

        item_exists_stmt = select(CartItemModel).where(
            CartItemModel.cart_id == cart.id,
            CartItemModel.movie_id == payload.movie_id
        )
        existing_item = await db.scalar(item_exists_stmt)
        if existing_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Movie is already in your cart."
            )

        new_item = CartItemModel(
            cart_id=cart.id,
            movie_id=payload.movie_id
        )
        db.add(new_item)

        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add item to cart."
            )
        await db.refresh(cart, ["items"])

        return {
            "status": "success",
            "message": f"'{movie.name}' added to cart.",
            "item_count": len(cart.items)
        }

    @staticmethod
    async def get_cart(db: AsyncSession, user_id: int):
        stmt = (
            select(CartModel)
            .where(CartModel.user_id == user_id)
            .options(
                selectinload(CartModel.items).joinedload(CartItemModel.movie)
            )
        )
        cart = await db.scalar(stmt)

        if not cart:
            return {
                "id": 0,
                "user_id": user_id,
                "items": [],
                "total_items": 0,
                "total_price": 0.0
            }

        total_price = sum(
            item.movie.price for item in cart.items if item.movie.price)
        total_items = len(cart.items)

        items_data = []
        for item in cart.items:
            items_data.append({
                "id": item.id,
                "movie_id": item.movie_id,
                "movie_name": item.movie.name,
                "price_at_addition": item.movie.price,
                "added_at": item.added_at
            })

        return {
            "id": cart.id,
            "user_id": cart.user_id,
            "items": items_data,
            "total_items": total_items,
            "total_price": round(total_price, 2)
        }

    @staticmethod
    async def remove_item(db: AsyncSession, user_id: int, item_id: int):
        stmt = (
            delete(CartItemModel)
            .where(
                CartItemModel.id == item_id,
                CartItemModel.cart_id == select(CartModel.id).where(
                    CartModel.user_id == user_id).scalar_subquery()
            )
        )
        result = await db.execute(stmt)
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in your cart."
            )

        return {"status": "success", "message": "Item removed from cart."}

    @staticmethod
    async def clear_cart(db: AsyncSession, user_id: int):
        cart_id_stmt = select(CartModel.id).where(CartModel.user_id == user_id)
        cart_id = await db.scalar(cart_id_stmt)

        if not cart_id:
            return {"status": "success", "message": "Cart is already empty."}

        stmt = delete(CartItemModel).where(CartItemModel.cart_id == cart_id)
        await db.execute(stmt)
        await db.commit()

        return {"status": "success", "message": "Cart cleared successfully."}