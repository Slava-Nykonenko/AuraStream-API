from decimal import Decimal

import pytest
import json
from unittest.mock import patch
from httpx import AsyncClient
from database.models.order import OrderModel, OrderStatus
from database.models.payments import PaymentsModel, PaymentStatus

BASE_URL = "/api/v1/webhooks/stripe"


@pytest.mark.asyncio
class TestPaymentWebhooks:
    @patch("stripe.Webhook.construct_event")
    @patch("services.payments.PaymentService._fulfill_payment")
    async def test_handle_checkout_session_completed(
            self, mock_fulfill, mock_construct, client: AsyncClient
    ):
        mock_event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "test_session_id",
                    "payment_intent": "pi_test_123"
                }
            }
        }
        mock_construct.return_value = mock_event

        headers = {"Stripe-Signature": "t=123,v1=test_sig"}
        payload = json.dumps(mock_event)

        response = await client.post(BASE_URL, content=payload,
                                     headers=headers)

        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        mock_fulfill.assert_called_once()

    @patch("stripe.Webhook.construct_event")
    async def test_webhook_invalid_signature(
            self, mock_construct, client: AsyncClient
    ):
        mock_construct.side_effect = Exception("Invalid signature")

        headers = {"Stripe-Signature": "invalid"}
        response = await client.post(
            BASE_URL, content="{}", headers=headers
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid webhook signature."

    async def test_fulfill_payment_logic(
            self, db_session, logged_in_active_user, test_movie
    ):
        from services.payments import PaymentService
        user, _, _ = logged_in_active_user

        order = OrderModel(user_id=user.id, total_amount=10.0,
                           status=OrderStatus.PENDING)
        db_session.add(order)
        await db_session.flush()

        payment = PaymentsModel(
            user_id=user.id,
            order_id=order.id,
            amount=Decimal("10.0"),
            status=PaymentStatus.CANCELED,
            external_payment_id="sess_123"
        )
        db_session.add(payment)
        await db_session.commit()

        await PaymentService._fulfill_payment(db=db_session,
                                              session_id="sess_123")

        await db_session.refresh(order)
        await db_session.refresh(payment)

        assert payment.status == PaymentStatus.SUCCESSFUL
        assert order.status == OrderStatus.PAID
