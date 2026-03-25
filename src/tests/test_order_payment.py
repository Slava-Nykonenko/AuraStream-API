from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient

ORDER_URL = "/api/v1/order"
PAYMENT_URL = "/api/v1/payments"
CART_URL = "/api/v1/cart"


@pytest.mark.asyncio
class TestOrderRoutes:
    async def test_place_order_success(self, client: AsyncClient, db_session,
                                       logged_in_active_user, test_movie):
        user, _, tokens = logged_in_active_user
        auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        await client.post(f"{CART_URL}/add", json={"movie_id": test_movie.id},
                          headers=auth_headers)

        response = await client.post(f"{ORDER_URL}/place_order",
                                     headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PENDING"
        assert data["total_amount"] == float(test_movie.price)
        assert len(data["items"]) == 1
        assert data["items"][0]["movie"]["id"] == test_movie.id

        cart_res = await client.get(f"{CART_URL}/me", headers=auth_headers)
        assert cart_res.json()["total_items"] == 0

    async def test_place_order_empty_cart_fails(self, client: AsyncClient,
                                                logged_in_active_user):
        _, _, tokens = logged_in_active_user
        response = await client.post(f"{ORDER_URL}/place_order", headers={
            "Authorization": f"Bearer {tokens['access_token']}"})

        assert response.status_code == 400
        assert response.json()["detail"] == "Your cart is empty."

    async def test_get_order_history(self, client: AsyncClient,
                                     logged_in_active_user, test_movie):
        user, _, tokens = logged_in_active_user
        auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        await client.post(f"{CART_URL}/add", json={"movie_id": test_movie.id},
                          headers=auth_headers)
        await client.post(f"{ORDER_URL}/place_order", headers=auth_headers)

        response = await client.get(f"{ORDER_URL}/my_orders",
                                    headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total_items"] >= 1

    async def test_cancel_order(self, client: AsyncClient,
                                logged_in_active_user, test_movie):
        user, _, tokens = logged_in_active_user
        auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        await client.post(f"{CART_URL}/add", json={"movie_id": test_movie.id},
                          headers=auth_headers)
        order_res = await client.post(f"{ORDER_URL}/place_order",
                                      headers=auth_headers)
        order_id = order_res.json()["id"]

        response = await client.delete(f"{ORDER_URL}/my_orders/{order_id}",
                                       headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "CANCELED"


@pytest.mark.asyncio
class TestPaymentRoutes:
    @patch("stripe.checkout.Session.create")
    async def test_create_checkout_session_success(self, mock_stripe,
                                                   client: AsyncClient,
                                                   logged_in_active_user,
                                                   test_movie):
        user, _, tokens = logged_in_active_user
        auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        await client.post(f"{CART_URL}/add", json={"movie_id": test_movie.id},
                          headers=auth_headers)
        order_res = await client.post(f"{ORDER_URL}/place_order",
                                      headers=auth_headers)
        order_id = order_res.json()["id"]

        mock_stripe.return_value = MagicMock(id="test_session_id",
                                             url="https://checkout.stripe.com/test")

        payload = {"order_id": order_id}
        response = await client.post(f"{PAYMENT_URL}/checkout", json=payload,
                                     headers=auth_headers)

        assert response.status_code == 201
        assert "checkout_url" in response.json()
        assert response.json()[
                   "checkout_url"] == "https://checkout.stripe.com/test"

    async def test_checkout_nonexistent_order_fails(self, client: AsyncClient,
                                                    logged_in_active_user):
        _, _, tokens = logged_in_active_user
        response = await client.post(
            f"{PAYMENT_URL}/checkout",
            json={"order_id": 99999},
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Order not found"

    async def test_payment_success_endpoint_404(self, client: AsyncClient):
        response = await client.get(f"{PAYMENT_URL}/success",
                                    params={"session_id": "invalid_session"})
        assert response.status_code == 404
        assert response.json()["detail"] == "Order not found"

    @patch("services.payments.PaymentService.cancel_payment")
    async def test_payment_cancel_endpoint(self, mock_cancel,
                                           client: AsyncClient,
                                           logged_in_active_user):
        mock_cancel.return_value = {"id": 1, "status": "CANCELED",
                                    "total_amount": 10.0,
                                    "created_at": "2026-03-25T12:00:00",
                                    "items": []}

        _, _, tokens = logged_in_active_user
        response = await client.get(
            f"{PAYMENT_URL}/cancel",
            params={"session_id": "some_session"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert response.status_code == 200
