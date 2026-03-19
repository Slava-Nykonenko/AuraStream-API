import asyncio
from datetime import datetime, timezone
from sqlalchemy import delete
from core.celery import celery_app
from database.session_postgresql import SessionLocal
from database.models.user import ActivationTokenModel, PasswordResetTokenModel


async def _cleanup_logic():
    async with SessionLocal() as db:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        await db.execute(
            delete(ActivationTokenModel).where(
                ActivationTokenModel.expires_at < now)
        )

        await db.execute(
            delete(PasswordResetTokenModel).where(
                PasswordResetTokenModel.expires_at < now)
        )

        await db.commit()


@celery_app.task(name="tasks.cleanup_tasks.cleanup_expired_tokens")
def cleanup_expired_tokens():
    asyncio.run(_cleanup_logic())
