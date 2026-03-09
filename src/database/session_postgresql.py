from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from core.settings import settings

SQLALCHEMY_DATABASE_URI = settings.DATABASE_URL

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URI,
    echo=True,
)

SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session:
        yield session
