"""Репозиторий для работы с реферальными ссылками."""

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy import case, delete, select, update

from bot.database import models
from bot.database.models import (
    Referral,
    ReferralLink,
    User,
)


class ReferralRepository:
    """Репозиторий для работы с реферальными ссылками."""

    @staticmethod
    async def create(user_id: int, invite_link: str) -> ReferralLink:
        """Создать реферальную ссылку."""
        async with models.async_session() as session:
            referral = ReferralLink(user_id=user_id, invite_link=invite_link)
            session.add(referral)
            await session.commit()
            await session.refresh(referral)
            return referral

    @staticmethod
    async def create_or_get_by_user_id(
        user_id: int,
        invite_link: str,
    ) -> tuple[ReferralLink, bool]:
        """
        Создать реферальную ссылку или вернуть уже существующую.

        Returns:
            (referral_link, created_now)
        """
        async with models.async_session() as session:
            referral = ReferralLink(user_id=user_id, invite_link=invite_link)
            session.add(referral)
            try:
                await session.commit()
                await session.refresh(referral)
                return referral, True
            except IntegrityError:
                await session.rollback()
                result = await session.execute(
                    select(ReferralLink).where(ReferralLink.user_id == user_id)
                )
                existing = result.scalar_one_or_none()
                if existing is None:
                    raise
                return existing, False

    @staticmethod
    async def get_by_user_id(user_id: int) -> Optional[ReferralLink]:
        """Получить реферальную ссылку пользователя."""
        async with models.async_session() as session:
            result = await session.execute(
                select(ReferralLink).where(ReferralLink.user_id == user_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def get_by_invite_link(invite_link: str) -> Optional[ReferralLink]:
        """Найти запись по ссылке."""
        async with models.async_session() as session:
            result = await session.execute(
                select(ReferralLink).where(ReferralLink.invite_link == invite_link)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def increment_count(referral_id: int) -> None:
        """Увеличить счётчик рефералов."""
        async with models.async_session() as session:
            await session.execute(
                update(ReferralLink)
                .where(ReferralLink.id == referral_id)
                .values(referral_count=ReferralLink.referral_count + 1)
            )
            await session.commit()

    @staticmethod
    async def decrement_count(referral_id: int) -> None:
        """Уменьшить счётчик рефералов (при выходе)."""
        async with models.async_session() as session:
            await session.execute(
                update(ReferralLink)
                .where(ReferralLink.id == referral_id)
                .where(ReferralLink.referral_count > 0)
                .values(referral_count=ReferralLink.referral_count - 1)
            )
            await session.commit()

    @staticmethod
    async def get_user_by_invite_link(invite_link: str) -> Optional[User]:
        """Получить владельца ссылки."""
        async with models.async_session() as session:
            result = await session.execute(
                select(User)
                .join(ReferralLink)
                .where(ReferralLink.invite_link == invite_link)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def claim_gift(referral_id: int, count: int = 1) -> None:
        """Увеличить счётчик полученных подарков."""
        async with models.async_session() as session:
            await session.execute(
                update(ReferralLink)
                .where(ReferralLink.id == referral_id)
                .values(gifts_claimed=ReferralLink.gifts_claimed + count)
            )
            await session.commit()

    @staticmethod
    async def release_claimed_gifts(referral_id: int, count: int) -> None:
        """Откатить зарезервированные подарки, если заявка не была доставлена админам."""
        if count <= 0:
            return

        async with models.async_session() as session:
            await session.execute(
                update(ReferralLink)
                .where(ReferralLink.id == referral_id)
                .values(
                    gifts_claimed=case(
                        (ReferralLink.gifts_claimed >= count, ReferralLink.gifts_claimed - count),
                        else_=0,
                    )
                )
            )
            await session.commit()

    @staticmethod
    async def claim_available_gifts(
        referral_id: int,
        referrals_per_gift: int,
    ) -> int:
        """
        Атомарно зафиксировать все доступные к выдаче подарки.

        Возвращает количество реально зафиксированных подарков.
        """
        if referrals_per_gift <= 0:
            return 0

        async with models.async_session() as session:
            for _ in range(5):
                result = await session.execute(
                    select(ReferralLink.referral_count, ReferralLink.gifts_claimed)
                    .where(ReferralLink.id == referral_id)
                )
                row = result.first()
                if not row:
                    return 0

                referral_count, gifts_claimed = row
                available = (referral_count // referrals_per_gift) - gifts_claimed
                if available <= 0:
                    return 0

                update_result = await session.execute(
                    update(ReferralLink)
                    .where(ReferralLink.id == referral_id)
                    .where(ReferralLink.gifts_claimed == gifts_claimed)
                    .values(gifts_claimed=gifts_claimed + available)
                )
                if update_result.rowcount and update_result.rowcount > 0:
                    await session.commit()
                    return available

                await session.rollback()

        return 0

    @staticmethod
    async def add_referral(referral_link_id: int, telegram_id: int) -> None:
        """Добавить запись о реферале."""
        async with models.async_session() as session:
            result = await session.execute(
                select(Referral).where(
                    Referral.referral_link_id == referral_link_id,
                    Referral.telegram_id == telegram_id,
                )
            )
            if result.scalar_one_or_none() is None:
                ref = Referral(referral_link_id=referral_link_id, telegram_id=telegram_id)
                session.add(ref)
                await session.commit()

    @staticmethod
    async def remove_referral(telegram_id: int) -> Optional[int]:
        """
        Удалить запись о реферале (при выходе из канала).
        Возвращает ID реферальной ссылки, если был найден и удалён.
        """
        async with models.async_session() as session:
            result = await session.execute(
                select(Referral).where(Referral.telegram_id == telegram_id)
            )
            referral = result.scalar_one_or_none()

            if referral:
                referral_link_id = referral.referral_link_id
                await session.execute(
                    delete(Referral).where(Referral.telegram_id == telegram_id)
                )
                await session.commit()
                return referral_link_id
            return None
