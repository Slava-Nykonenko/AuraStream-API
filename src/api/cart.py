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


@router.post(
    "/add",
    response_model=CartActionResponseSchema,
    summary="Add Movie to Cart",
    description="Adds a specific movie to the authenticated user's shopping "
                "cart. The system validates that the movie is not already in "
                "the cart and that the user does not already own the movie."
)
async def add_movie_to_cart(
        payload: CartItemCreateSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user),
):
    return await CartService.add_item(
        db=db, user_id=current_user.id, payload=payload
    )


@router.get(
    "/me",
    response_model=CartReadSchema,
    summary="View My Cart",
    description="Retrieves a detailed view of the user's current shopping "
                "cart, including a list of items, individual prices at the "
                "time of addition, and the total calculated price."
)
async def view_my_cart(
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    return await CartService.get_cart(db=db, user_id=current_user.id)


@router.delete(
    "/items/{item_id}",
    response_model=CartActionResponseSchema,
    summary="Remove Specific Item",
    description="Removes a single item from the cart using its unique item "
                "ID. Returns the updated total item count to sync the UI."
)
async def remove_cart_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await CartService.remove_item(
        db=db, user_id=current_user.id, item_id=item_id)
    cart = await CartService.get_cart(db=db, user_id=current_user.id)
    return {**result, "item_count": cart["total_items"]}


@router.delete(
    "/clear",
    response_model=CartActionResponseSchema,
    summary="Empty Shopping Cart",
    description="Performs a batch deletion of all items associated with the "
                "user's cart. Use this to reset the cart state before or "
                "after order placement."
)
async def clear_my_cart(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await CartService.clear_cart(db=db, user_id=current_user.id)
    return {**result, "item_count": 0}
