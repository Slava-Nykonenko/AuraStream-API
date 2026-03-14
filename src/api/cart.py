from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from database.models.user import UserModel
from database.session_postgresql import get_db
from schemas.cart import (
    CartReadSchema,
    CartActionResponseSchema,
    CartItemCreateSchema
)
from services.cart import CartService

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/add", response_model=CartActionResponseSchema)
async def add_movie_to_cart(
        payload: CartItemCreateSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user),
):
    return await CartService.add_item(
        db=db, user_id=current_user.id, payload=payload
    )


@router.get("/me", response_model=CartReadSchema)
async def view_my_cart(
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    return await CartService.get_cart(db=db, user_id=current_user.id)


@router.delete("/items/{item_id}", response_model=CartActionResponseSchema)
async def remove_cart_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await CartService.remove_item(
        db=db, user_id=current_user.id, item_id=item_id)
    cart = await CartService.get_cart(db=db, user_id=current_user.id)
    return {**result, "item_count": cart["total_items"]}


@router.delete("/clear", response_model=CartActionResponseSchema)
async def clear_my_cart(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await CartService.clear_cart(db=db, user_id=current_user.id)
    return {**result, "item_count": 0}
