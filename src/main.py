from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.admin import router as admin_router
from api.auth import router as auth_router
from api.cart import router as cart_router
from api.movies import router as movies_router
from api.order import router as order_router
from api.social import router as social_router
from api.payments import router as payments_router
from api.webhooks import router as webhooks_router
from database.session_postgresql import SessionLocal
from database.utils import seed_basic_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as session:
        await seed_basic_data(session)
    yield

app = FastAPI(lifespan=lifespan)

api_version_prefix = "/api/v1"

app.include_router(movies_router, prefix=api_version_prefix)
app.include_router(auth_router, prefix=api_version_prefix)
app.include_router(admin_router, prefix=api_version_prefix)
app.include_router(social_router, prefix=api_version_prefix)
app.include_router(cart_router, prefix=api_version_prefix)
app.include_router(order_router, prefix=api_version_prefix)
app.include_router(payments_router, prefix=api_version_prefix)
app.include_router(webhooks_router, prefix=api_version_prefix)
