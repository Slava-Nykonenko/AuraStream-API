from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from database.models.user import UserModel
from database.session_postgresql import get_db
from schemas.order import OrderDetailSchema, OrderListSchema
from schemas.responses import ORDER_ERRORS, AUTH_ERRORS
from services.order import OrderService

router = APIRouter(prefix="/order", tags=["order"])


@router.post(
    "/place_order",
    response_model=OrderDetailSchema,
    summary="Place an Order",
    description="Converts the current user's shopping cart into a formal "
                "order record. Upon successful placement, the order is set "
                "to 'PENDING' and the shopping cart is emptied.",
    responses={**ORDER_ERRORS, **AUTH_ERRORS}
)
async def place_order(
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    return await OrderService.place_order(db=db, user_id=current_user.id)


@router.get(
    "/my_orders",
    response_model=OrderListSchema,
    summary="View My Orders",
    description="Retrieves a paginated list of all orders placed by the "
                "currently authenticated user, including their current "
                "status and creation date.",
    responses={**ORDER_ERRORS, **AUTH_ERRORS}
)
async def get_my_orders(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user),
        page: int = 1,
        per_page: int = 20
):
    return await OrderService.get_order_history(
        request=request,
        db=db,
        user=current_user,
        page=page,
        per_page=per_page
    )


@router.get(
    "/my_orders/{order_id}",
    response_model=OrderDetailSchema,
    summary="Get Order Details",
    description="Returns a comprehensive breakdown of a specific order, "
                "including detailed information about every movie title "
                "included in the purchase.",
    responses={**ORDER_ERRORS, **AUTH_ERRORS}
)
async def order_detail(
        order_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    return await OrderService.get_order_details(
        db=db, order_id=order_id, user=current_user
    )


@router.delete(
    "/my_orders/{order_id}",
    response_model=OrderDetailSchema,
    summary="Cancel Order",
    description="Updates the status of a specific order to 'CANCELED'. This "
                "action also updates all associated order items to ensure "
                "consistency across the system.",
    responses={**ORDER_ERRORS, **AUTH_ERRORS}
)
async def cancel_order(
        order_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    return await OrderService.cancel_order(
        db=db, order_id=order_id, user_id=current_user.id
    )
