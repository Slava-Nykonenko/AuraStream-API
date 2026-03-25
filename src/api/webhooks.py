from fastapi import APIRouter, Request, Header, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session_postgresql import get_db
from services.payments import PaymentService


router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db)
):
    payload = await request.body()
    return await PaymentService.handle_webhook(
        db=db, payload=payload, sig_header=stripe_signature
    )
