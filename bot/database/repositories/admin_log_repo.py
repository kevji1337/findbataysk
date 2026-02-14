"""Репозиторий для журнала действий админов."""

from typing import Optional

from sqlalchemy import select

from bot.database.models import AdminActionLog, async_session


class AdminActionLogRepository:
    """Репозиторий для журнала действий админов."""

    @staticmethod
    async def create(
        admin_telegram_id: int,
        action_type: str,
        target_type: str,
        target_id: int,
        details: Optional[str] = None,
    ) -> AdminActionLog:
        """Записать событие в журнал."""
        async with async_session() as session:
            log = AdminActionLog(
                admin_telegram_id=admin_telegram_id,
                action_type=action_type,
                target_type=target_type,
                target_id=target_id,
                details=details,
            )
            session.add(log)
            await session.commit()
            await session.refresh(log)
            return log

    @staticmethod
    async def get_recent(limit: int = 50) -> list[AdminActionLog]:
        """Получить последние события журнала."""
        async with async_session() as session:
            result = await session.execute(
                select(AdminActionLog)
                .order_by(AdminActionLog.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
