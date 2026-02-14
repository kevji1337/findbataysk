"""Репозиторий для работы с заявками на рекламу."""

from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select, update

from bot.database.models import AdvertisingRequest, User, async_session


class AdvertisingRepository:
    """Репозиторий для работы с заявками на рекламу."""

    @staticmethod
    async def create(user_id: int, channel_link: str) -> AdvertisingRequest:
        """Создать заявку на рекламу."""
        async with async_session() as session:
            request = AdvertisingRequest(user_id=user_id, channel_link=channel_link)
            session.add(request)
            await session.commit()
            await session.refresh(request)
            return request

    @staticmethod
    async def get_by_id(request_id: int) -> Optional[AdvertisingRequest]:
        """Получить заявку по ID."""
        async with async_session() as session:
            result = await session.execute(
                select(AdvertisingRequest).where(AdvertisingRequest.id == request_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def update_status(request_id: int, status: str) -> bool:
        """
        Обновить статус заявки только если она ещё pending.

        Возвращает True, если статус реально изменён.
        """
        async with async_session() as session:
            result = await session.execute(
                update(AdvertisingRequest)
                .where(AdvertisingRequest.id == request_id)
                .where(AdvertisingRequest.status == "pending")
                .values(
                    status=status,
                    reviewed_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            await session.commit()
            return bool(result.rowcount and result.rowcount > 0)

    @staticmethod
    async def get_all_requests(
        limit: int = 20,
        status_filter: Optional[str] = None,
    ) -> list[tuple[AdvertisingRequest, User]]:
        """Получить историю заявок с информацией о пользователях."""
        async with async_session() as session:
            query = (
                select(AdvertisingRequest, User)
                .join(User)
                .order_by(AdvertisingRequest.created_at.desc())
            )
            if status_filter:
                query = query.where(AdvertisingRequest.status == status_filter)
            query = query.limit(limit)

            result = await session.execute(query)
            return result.all()

    @staticmethod
    async def get_pending_count() -> int:
        """Получить количество ожидающих заявок."""
        async with async_session() as session:
            result = await session.execute(
                select(func.count(AdvertisingRequest.id))
                .where(AdvertisingRequest.status == "pending")
            )
            return result.scalar() or 0

    @staticmethod
    async def get_user_requests_count(user_id: int, hours: int = 1) -> int:
        """Получить количество заявок пользователя за последние N часов."""
        async with async_session() as session:
            cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)
            result = await session.execute(
                select(func.count(AdvertisingRequest.id))
                .where(AdvertisingRequest.user_id == user_id)
                .where(AdvertisingRequest.created_at >= cutoff)
            )
            return result.scalar() or 0
