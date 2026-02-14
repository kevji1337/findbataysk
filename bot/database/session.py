"""Управление сессиями БД с поддержкой Unit of Work."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import async_session


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager для работы с сессией БД.
    
    Автоматически коммитит при успехе и откатывает при ошибке.
    Используй это вместо прямого async_session() для транзакционности.
    
    Usage:
        async with get_session() as session:
            user = await UserRepository.get_by_id(session, user_id)
            await ReferralRepository.increment_count(session, ref_id)
            # Всё в одной транзакции!
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    Генератор сессии для dependency injection.
    
    Можно использовать для middleware или DI-контейнеров.
    """
    async with get_session() as session:
        yield session
