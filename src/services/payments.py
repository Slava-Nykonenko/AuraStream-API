from decimal import Decimal

import stripe
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette.requests import Request

from core.settings import settings
from database.models.order import (
    OrderModel,
    OrderStatus,
    OrderItemModel,
)
from database.models.payments import PaymentsModel, PaymentStatus, PaymentItems
from database.models.user import UserModel
from schemas.payments import (
    PaymentListSchema,
    PaymentReadSchema,
    CheckoutRequestSchema
)
from tasks.email_tasks import send_email
from utils.service_helpers import pagination_helper

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentService:
    @staticmethod
    async def create_checkout_session(
            db: AsyncSession,
            payload: CheckoutRequestSchema,
            user_id: int,
    ):
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == payload.order_id)
            .options(
                joinedload(OrderModel.items)
                .selectinload(OrderItemModel.movie)
            )
        )
        result = await db.execute(stmt)
        order = result.unique().scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        if payload.item_ids:
            items_to_pay = [
                item for item in order.items if item.id in payload.item_ids
            ]
        else:
            items_to_pay = order.items

        if not items_to_pay:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid items selected for payment"
            )
        line_items = []
        total_amount = 0
        for item in items_to_pay:
            unit_amount = int(item.price_paid * 100)
            total_amount += item.price_paid

            line_items.append({
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": f"Movie Access: ID {item.movie_id}"},
                    "unit_amount": unit_amount,
                },
                "quantity": 1,
            })
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=f"{settings.BASE_URL}/payments/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.BASE_URL}/payments/cancel",
                metadata={
                    "order_id": order.id,
                    "user_id": user_id
                }
            )

            new_payment = PaymentsModel(
                user_id=user_id,
                order_id=order.id,
                amount=total_amount,
                status=PaymentStatus.SUCCESSFUL,
                external_payment_id=session.id
            )
            db.add(new_payment)
            await db.flush()

            for item in items_to_pay:
                payment_item = PaymentItems(
                    payment_id=new_payment.id,
                    order_item_id=item.id,
                    price_at_payment=Decimal(str(item.price_paid))
                )
                db.add(payment_item)

            await db.commit()
            return session.url

        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Stripe Gateway Error: {str(e)}"
            )

    @staticmethod
    async def handle_webhook(db: AsyncSession, payload, sig_header):
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature."
            )

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            await PaymentService._fulfill_payment(
                db=db, session_id=session["id"]
            )

        return {"status": "success"}

    @staticmethod
    async def _fulfill_payment(db: AsyncSession, session_id: str):
        stmt = (
            select(PaymentsModel)
            .where(PaymentsModel.external_payment_id == session_id)
            .options(
                joinedload(PaymentsModel.payment_items),
                joinedload(PaymentsModel.user).joinedload(UserModel.profile)
            )
        )
        result = await db.execute(stmt)
        payment = result.unique().scalar_one_or_none()

        if not payment:
            return

        payment.status = PaymentStatus.SUCCESSFUL

        sum_stmt = select(func.sum(PaymentsModel.amount)).where(
            PaymentsModel.order_id == payment.order_id,
            PaymentsModel.status == PaymentStatus.SUCCESSFUL
        )
        total_paid = (await db.execute(sum_stmt)).scalar() or Decimal("0.00")
        order_stmt = select(OrderModel).where(
            OrderModel.id == payment.order_id
        )
        order = (await db.execute(order_stmt)).scalar_one()

        order_total = Decimal(str(order.total_amount))

        if total_paid >= order_total:
            order.status = OrderStatus.PAID
        else:
            order.status = OrderStatus.PARTIALLY_PAID

        await db.commit()

        user_profile = payment.user.profile
        first_name = user_profile.first_name if user_profile else "Customer"
        body_data = {
            "user_name": first_name,
            "order_id": payment.order_id,
            "amount": f"{payment.amount:.2f}",
            "library_url": f"{settings.BASE_URL}/my-library"
        }

        send_email.delay(
            email=payment.user.email,
            body_data=body_data,
            msg_type="payment_success"
        )
        return {"status": "success"}

    @staticmethod
    async def get_payment_history(
            request: Request,
            db: AsyncSession,
            user_id: int,
            page: int,
            per_page: int
    ):
        stmt = select(PaymentsModel).where(
            PaymentsModel.user_id == user_id).order_by(
            PaymentsModel.created_at.desc())

        result = await pagination_helper(request, page, per_page, db, stmt)
        return PaymentListSchema(
            items=[PaymentReadSchema.model_validate(payment) for payment in
                   result["items"]],
            **{key: value for key, value in result.items() if key != "items"}
        )

    @staticmethod
    async def list_all_payments_admin(
            request: Request,
            db: AsyncSession,
            page: int,
            per_page: int,
            filters: dict
    ):
        stmt = select(PaymentsModel).options(joinedload(PaymentsModel.user))

        if filters.get("user_id"):
            stmt = stmt.where(PaymentsModel.user_id == filters["user_id"])
        if filters.get("status"):
            stmt = stmt.where(PaymentsModel.status == filters["status"])
        if filters.get("date_from"):
            stmt = stmt.where(PaymentsModel.created_at >= filters["date_from"])

        stmt = stmt.order_by(PaymentsModel.created_at.desc())

        return await pagination_helper(request, page, per_page, db, stmt)

    @staticmethod
    async def get_order_by_stripe_session(db: AsyncSession, session_id: str):
        stmt = (
            select(OrderModel)
            .join(PaymentsModel, PaymentsModel.order_id == OrderModel.id)
            .where(PaymentsModel.external_payment_id == session_id)
            .options(
                joinedload(OrderModel.items).joinedload(
                    OrderItemModel.movie),
                joinedload(OrderModel.user)
            )
        )

        result = await db.execute(stmt)
        order = result.unique().scalar_one_or_none()

        return order
