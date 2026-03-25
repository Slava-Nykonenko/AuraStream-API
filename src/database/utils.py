from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.user import UserGroupModel
from database.models.user import UserGroupEnum


async def seed_basic_data(db: AsyncSession):
    for group_name in UserGroupEnum:
        stmt = select(UserGroupModel).where(UserGroupModel.name == group_name)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            db.add(UserGroupModel(name=group_name))

    await db.commit()
