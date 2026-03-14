from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from database.models.user import UserModel
from database.session_postgresql import get_db
from schemas.order import OrderDetailSchema, OrderListSchema
from services.order import OrderService

router = APIRouter(prefix="/order", tags=["order"])


@router.post("/place_order", response_model=OrderDetailSchema)
async def place_order(
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    return await OrderService.place_order(db=db, user_id=current_user.id)


@router.get("/my_orders", response_model=List[OrderListSchema])
async def get_my_orders(
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    return await OrderService.get_order_history(db=db, user_id=current_user.id)


@router.get("/my_orders/{order_id}", response_model=OrderDetailSchema)
async def order_detail(
        order_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    return await OrderService.get_order_details(
        db=db, order_id=order_id, user_id=current_user.id
    )


@router.delete("/my_orders/{order_id}", response_model=OrderDetailSchema)
async def cancel_order(
        order_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    return await OrderService.cancel_order(
        db=db, order_id=order_id, user_id=current_user.id
    )
