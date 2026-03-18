from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from database.models.user import UserModel
from database.session_postgresql import get_db
from schemas.order import OrderDetailSchema
from schemas.payments import CheckoutRequestSchema
from services.payments import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def create_payment_intent(
        payload: CheckoutRequestSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    checkout_url = await PaymentService.create_checkout_session(
        db=db,
        payload=payload,
        user_id=current_user.id
    )
    return {"checkout_url": checkout_url}


@router.get("/success", response_model=OrderDetailSchema)
async def success(
        session_id: str,
        db: AsyncSession = Depends(get_db)
):
    order = await PaymentService.get_order_by_stripe_session(
        db=db, session_id=session_id
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order


@router.get("/cancel", response_model=OrderDetailSchema)
async def cancel_payment(
        session_id: str,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    return await PaymentService.cancel_payment(
        session_id=session_id, db=db, current_user=current_user
    )