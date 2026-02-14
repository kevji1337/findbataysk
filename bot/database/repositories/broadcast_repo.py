"""Репозиторий фоновых задач рассылки."""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select, update

from bot.database import models
from bot.database.models import BroadcastJob


class BroadcastJobRepository:
    """Репозиторий фоновых задач рассылки."""

    @staticmethod
    async def create(
        *,
        admin_telegram_id: int,
        source_chat_id: int,
        source_message_id: int,
        total_users: int,
        throttle_seconds: float = 0.05,
        max_retries: int = 3,
    ) -> BroadcastJob:
        async with models.async_session() as session:
            job = BroadcastJob(
                created_by_admin_id=admin_telegram_id,
                source_chat_id=source_chat_id,
                source_message_id=source_message_id,
                status="pending",
                total_users=total_users,
                throttle_seconds=throttle_seconds,
                max_retries=max_retries,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            return job

    @staticmethod
    async def get_by_id(job_id: int) -> Optional[BroadcastJob]:
        async with models.async_session() as session:
            result = await session.execute(
                select(BroadcastJob).where(BroadcastJob.id == job_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def acquire_next_pending() -> Optional[BroadcastJob]:
        """Взять ближайшую pending-задачу и перевести в processing."""
        async with models.async_session() as session:
            job = await session.scalar(
                select(BroadcastJob)
                .where(BroadcastJob.status == "pending")
                .order_by(BroadcastJob.id.asc())
                .with_for_update(skip_locked=True)
            )
            if not job:
                return None

            if job.total_users <= 0:
                job.status = "done"
                job.started_at = datetime.now(UTC).replace(tzinfo=None)
                job.finished_at = datetime.now(UTC).replace(tzinfo=None)
            else:
                job.status = "processing"
                job.started_at = datetime.now(UTC).replace(tzinfo=None)
            await session.commit()
            await session.refresh(job)
            return job

    @staticmethod
    async def increment_progress(
        *,
        job_id: int,
        sent_delta: int = 0,
        blocked_delta: int = 0,
        failed_delta: int = 0,
    ) -> None:
        async with models.async_session() as session:
            await session.execute(
                update(BroadcastJob)
                .where(BroadcastJob.id == job_id)
                .values(
                    processed_users=BroadcastJob.processed_users + 1,
                    sent_count=BroadcastJob.sent_count + sent_delta,
                    blocked_count=BroadcastJob.blocked_count + blocked_delta,
                    failed_count=BroadcastJob.failed_count + failed_delta,
                )
            )
            await session.commit()

    @staticmethod
    async def mark_done(job_id: int) -> None:
        async with models.async_session() as session:
            await session.execute(
                update(BroadcastJob)
                .where(BroadcastJob.id == job_id)
                .values(
                    status="done",
                    finished_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            await session.commit()

    @staticmethod
    async def mark_retry_or_failed(job_id: int, error_text: str) -> None:
        """Увеличить retry_count и пометить failed, если лимит превышен."""
        async with models.async_session() as session:
            job = await session.scalar(
                select(BroadcastJob).where(BroadcastJob.id == job_id)
            )
            if not job:
                return

            job.retry_count += 1
            job.last_error = error_text[:4000]
            if job.retry_count > job.max_retries:
                job.status = "failed"
                job.finished_at = datetime.now(UTC).replace(tzinfo=None)
            else:
                job.status = "pending"
            await session.commit()
