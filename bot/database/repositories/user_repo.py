"""Репозиторий для работы с пользователями."""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select, update

from bot.database import models
from bot.database.models import User


class UserRepository:
    """Репозиторий для работы с пользователями."""

    @staticmethod
    async def get_or_create(
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> User:
        """Получить или создать пользователя."""
        async with models.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            else:
                changed = False
                if username != user.username:
                    user.username = username
                    changed = True
                if first_name != user.first_name:
                    user.first_name = first_name
                    changed = True
                if user.bot_blocked:
                    user.bot_blocked = False
                    user.blocked_at = None
                    changed = True
                if changed:
                    await session.commit()
                    await session.refresh(user)

            return user

    @staticmethod
    async def get_by_telegram_id(telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID."""
        async with models.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(user_id: int) -> Optional[User]:
        """Получить пользователя по внутреннему ID."""
        async with models.async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def get_all_telegram_ids() -> list[int]:
        """Получить Telegram ID всех пользователей."""
        async with models.async_session() as session:
            result = await session.execute(select(User.telegram_id))
            return list(result.scalars().all())

    @staticmethod
    async def get_broadcast_telegram_ids() -> list[int]:
        """Получить пользователей для рассылки (исключая bot_blocked)."""
        async with models.async_session() as session:
            result = await session.execute(
                select(User.telegram_id).where(User.bot_blocked.is_(False))
            )
            return list(result.scalars().all())

    @staticmethod
    async def mark_bot_blocked(telegram_id: int) -> None:
        """Пометить пользователя как заблокировавшего бота."""
        async with models.async_session() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(bot_blocked=True, blocked_at=datetime.now(UTC).replace(tzinfo=None))
            )
            await session.commit()
