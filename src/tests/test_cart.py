import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.cart import CartItemModel
from database.models.movies import MoviesModel
from database.models.order import OrderModel, OrderItemModel, OrderStatus
from database.models.user import UserModel

pytestmark = pytest.mark.asyncio

BASE_URL = "/api/v1/cart"


class TestCartRoutes:
    @staticmethod
    async def get_cart(
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]],
            client: AsyncClient,
            test_movie: MoviesModel
    ):
        _, _, tokens = logged_in_active_user
        await client.post(
            url=f"{BASE_URL}/add",
            json={"movie_id": test_movie.id},
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        response = await client.get(
            url=f"{BASE_URL}/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        return response, tokens

    async def test_view_empty_cart(
            self, client: AsyncClient,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]],
    ):
        user, _, tokens = logged_in_active_user
        response = await client.get(
            url=f"{BASE_URL}/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user.id
        assert data["items"] == []
        assert data["total_items"] == 0
        assert data["total_price"] == 0.0

    async def test_add_item_to_cart(
            self, client: AsyncClient,
            db_session: AsyncSession,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]],
            test_movie: MoviesModel
    ):
        _, _, tokens = logged_in_active_user
        payload = {"movie_id": test_movie.id}
        response = await client.post(
            url=f"{BASE_URL}/add",
            json=payload,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["item_count"] == 1
        assert test_movie.name in data["message"]

    async def test_add_nonexistent_movie(
            self, client: AsyncClient,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]]
    ):
        _, _, tokens = logged_in_active_user
        payload = {"movie_id": 99999}
        response = await client.post(
            url=f"{BASE_URL}/add",
            json=payload,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Movie not found."

    async def test_prevent_duplicate_cart_items(
            self,
            client: AsyncClient,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]],
            test_movie: MoviesModel
    ):
        _, _, tokens = logged_in_active_user
        payload = {"movie_id": test_movie.id}

        await client.post(
            url=f"{BASE_URL}/add",
            json=payload,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        response = await client.post(
            url=f"{BASE_URL}/add",
            json=payload,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Movie is already in your cart."

    async def test_prevent_adding_owned_movie(
            self,
            client: AsyncClient,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]],
            db_session: AsyncSession,
            test_movie: MoviesModel
    ):
        user, _, tokens = logged_in_active_user
        order = OrderModel(
            user_id=user.id,
            total_amount=float(test_movie.price),
            status=OrderStatus.PAID
        )
        db_session.add(order)
        await db_session.flush()

        order_item = OrderItemModel(
            order_id=order.id,
            movie_id=test_movie.id,
            price_paid=float(test_movie.price)
        )
        db_session.add(order_item)
        await db_session.commit()

        payload = {"movie_id": test_movie.id}
        response = await client.post(
            url=f"{BASE_URL}/add",
            json=payload,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}

        )
        assert response.status_code == 400
        assert response.json()["detail"] == "You already own this movie."

    async def test_view_populated_cart(
            self,
            client: AsyncClient,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]],
            test_movie: MoviesModel
    ):
        response, _ = await self.get_cart(
            logged_in_active_user, client, test_movie
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_items"] == 1
        assert data["total_price"] == float(test_movie.price)
        assert len(data["items"]) == 1
        assert data["items"][0]["movie_id"] == test_movie.id
        assert "price_at_addition" in data["items"][0]

    async def test_remove_cart_item(
            self, client: AsyncClient,
            db_session: AsyncSession,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]],
            test_movie: MoviesModel
    ):
        cart_response, tokens = await self.get_cart(
            logged_in_active_user, client, test_movie
        )
        cart_item_id = cart_response.json()["items"][0]["id"]

        delete_response = await client.delete(
            url=f"{BASE_URL}/items/{cart_item_id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["item_count"] == 0

        cart_stmt = select(CartItemModel).where(
            CartItemModel.id == cart_item_id
        )
        result = await db_session.execute(cart_stmt)
        assert result.scalar_one_or_none() is None

    async def test_remove_nonexistent_cart_item(
            self,
            client: AsyncClient,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]]
    ):
        _, _, tokens = logged_in_active_user
        response = await client.delete(
            url=f"{BASE_URL}/items/99999",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Item not found in your cart."

    async def test_clear_cart(
            self, client: AsyncClient,
            db_session: AsyncSession,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]],
            test_movie: MoviesModel
    ):
        _, _, tokens = logged_in_active_user
        await client.post(
            url=f"{BASE_URL}/add",
            json={"movie_id": test_movie.id},
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        response = await client.delete(
            url=f"{BASE_URL}/clear",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert response.status_code == 200
        assert response.json()["item_count"] == 0
        assert response.json()["message"] == "Cart cleared successfully."

        check_cart = await client.get(
            url=f"{BASE_URL}/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert check_cart.json()["total_items"] == 0
