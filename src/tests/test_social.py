import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta

from database.models.movies import MoviesModel
from database.models.user import UserProfileModel, user_favorites, UserModel
from services.social import SocialService

BASE_URL = "/api/v1/social"


@pytest.mark.asyncio
class TestSocialRoutes:

    async def test_create_profile_success(
            self, client: AsyncClient,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]]
    ):
        _, _, tokens = logged_in_active_user
        payload = {
            "first_name": "john",
            "last_name": "smith",
            "info": "Test User Info",
            "gender": "MAN",
            "date_of_birth": str(date.today() - timedelta(days=365 * 30)),
            "avatar": "https://example.com/avatar.png"
        }

        response = await client.post(
            f"{BASE_URL}/me/profile",
            json=payload,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Smith"
        assert data["user_id"] is not None

    async def test_prevent_duplicate_profile(
            self, client: AsyncClient,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]]
    ):
        _, _, tokens = logged_in_active_user
        payload = {
            "first_name": "Test",
            "last_name": "User",
            "date_of_birth": "1990-01-01"
        }

        await client.post(
            f"{BASE_URL}/me/profile",
            json=payload,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        response = await client.post(
            f"{BASE_URL}/me/profile",
            json=payload,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "You already have a profile."

    async def test_create_profile_underage_validation(
            self,
            client: AsyncClient,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]]
    ):
        _, _, tokens = logged_in_active_user
        payload = {
            "first_name": "Young",
            "last_name": "User",
            "date_of_birth": str(date.today() - timedelta(days=365 * 10))
            # 10 years old
        }

        response = await client.post(
            f"{BASE_URL}/me/profile",
            json=payload,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert response.status_code == 422
        assert "at least 16 years old" in response.text

    async def test_get_profiles_list(
            self, client: AsyncClient,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]]
    ):
        _, _, tokens = logged_in_active_user
        response = await client.get(
            f"{BASE_URL}/profiles",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_get_specific_profile(
            self, client: AsyncClient,
            db_session: AsyncSession,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]]
    ):
        user, _, tokens = logged_in_active_user

        profile = UserProfileModel(
            user_id=user.id,
            first_name="Alex",
            last_name="Tester",
            date_of_birth=date(1995, 1, 1)
        )
        db_session.add(profile)
        await db_session.commit()

        response = await client.get(
            f"{BASE_URL}/profiles/{profile.id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )

        assert response.status_code == 200
        assert response.json()["first_name"] == "Alex"


@pytest.mark.asyncio
class TestSocialServiceLogic:
    async def test_toggle_favorite_logic(
            self, db_session: AsyncSession,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]],
            test_movie: MoviesModel
    ):
        user, _, _ = logged_in_active_user

        status = await SocialService.toggle_favorite(
            db_session, user.id, test_movie.id
        )
        assert status == "added to"

        stmt = select(user_favorites).where(
            user_favorites.c.user_id == user.id
        )
        result = await db_session.execute(stmt)
        assert result.first() is not None

        status = await SocialService.toggle_favorite(
            db_session, user.id, test_movie.id
        )
        assert status == "removed from"

    async def test_add_comment_logic(
            self, db_session: AsyncSession,
            logged_in_active_user: tuple[UserModel, dict[str], dict[str]],
            test_movie: MoviesModel
    ):
        user, _, _ = logged_in_active_user
        content = "This is a test comment"

        comment = await SocialService.add_comment(
            db_session, user.id, test_movie.id, content
        )

        assert comment.id is not None
        assert comment.content == content
        assert comment.movie_id == test_movie.id
