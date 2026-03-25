import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from core.celery import celery_app
from database.models.base import Base
from database.models.movies import MoviesModel
from database.models.user import UserModel, UserGroupModel, UserGroupEnum
from database.session_postgresql import get_db
from database.utils import seed_basic_data
from main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = async_sessionmaker(engine_test, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        await seed_basic_data(session)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def disable_celery_tasks(monkeypatch):
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@pytest_asyncio.fixture
async def registered_user(client, db_session):
    unique_id = uuid.uuid4().hex[:6]
    payload = {
        "email": f"user_{unique_id}@test.com",
        "password": "Test1@Password"
    }
    await client.post(
        "/api/v1/auth/register",
        json=payload
    )
    user = await db_session.scalar(
        select(UserModel).where(UserModel.email == payload["email"])
    )
    return user, payload


@pytest_asyncio.fixture
async def logged_in_active_user(client, db_session, registered_user):
    user, payload = registered_user
    user.is_active = True
    await db_session.commit()
    await db_session.refresh(user)
    token_pair = await client.post(
        url=f"/api/v1/auth/login",
        json=payload
    )
    return user, payload, token_pair.json()


@pytest_asyncio.fixture
async def admin_user(client, db_session):
    payload = {
        "email": "admin@test.com",
        "password": "Admin1!Password",
    }
    await client.post(
        url=f"/api/v1/auth/register",
        json=payload,
    )
    admin = await db_session.scalar(
        select(UserModel).where(UserModel.email == payload["email"])
    )
    admin.is_active = True
    group_stmt = select(UserGroupModel).where(
        UserGroupModel.name == UserGroupEnum.ADMIN
    )
    group_result = await db_session.execute(group_stmt)
    group_db = group_result.scalar_one_or_none()
    admin.group_id = group_db.id
    await db_session.commit()
    await db_session.refresh(admin)
    token_pair = await client.post(
        url="/api/v1/auth/login",
        json=payload
    )
    return admin, payload, token_pair.json()

@pytest_asyncio.fixture
async def sample_movie_data():
    return {
        "name": f"Inception {uuid.uuid4()}",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "description": "test movie description",
        "votes": 2000000,
        "meta_score": 74.0,
        "gross": 292.6,
        "price": "14.99",
        "certification": "PG-13",
        "genres": ["Action", "Sci-Fi"],
        "stars": ["Leonardo DiCaprio"],
        "directors": ["Christopher Nolan"]
    }

@pytest_asyncio.fixture
async def test_movie(client, db_session, sample_movie_data, admin_user):
    payload = sample_movie_data
    _, _, token_pair = admin_user
    await client.post(
        url="/api/v1/movie_theater/movies",
        json=payload,
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    return await db_session.scalar(
        select(MoviesModel).where(MoviesModel.name == payload["name"])
    )

@pytest_asyncio.fixture
async def logged_in_user_with_profile(
        client, db_session, logged_in_active_user
):
    user, _, token_pair = logged_in_active_user
    await client.post(
        url="/api/v1/social/me/profile",
        json={
            "first_name": "Jessica",
            "last_name": "Smith",
            "avatar": "http://test.com/example/avatar.jpg",
            "info": "Test User Info",
            "gender": "WOMAN",
            "date_of_birth": "2006-03-25"
        },
        headers={"Authorization": f"Bearer {token_pair['access_token']}"}
    )
    return user, token_pair
