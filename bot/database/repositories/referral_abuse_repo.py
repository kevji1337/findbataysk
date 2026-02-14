"""Репозиторий для антиабьюз-логики реферальной системы."""

from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select

from bot.database.models import (
    ReferralAbuseFlag,
    ReferralActivityLog,
    async_session,
)


class ReferralAbuseRepository:
    """Репозиторий для антиабьюз-логики реферальной системы."""

    @staticmethod
    async def add_activity(
        telegram_id: int,
        referral_link_id: int,
        action: str,
        is_rejoin: bool = False,
    ) -> None:
        async with async_session() as session:
            session.add(
                ReferralActivityLog(
                    telegram_id=telegram_id,
                    referral_link_id=referral_link_id,
                    action=action,
                    is_rejoin=is_rejoin,
                )
            )
            await session.commit()

    @staticmethod
    async def count_recent_link_actions(
        referral_link_id: int,
        action: str,
        window_minutes: int,
    ) -> int:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=window_minutes)
        async with async_session() as session:
            result = await session.execute(
                select(func.count(ReferralActivityLog.id))
                .where(ReferralActivityLog.referral_link_id == referral_link_id)
                .where(ReferralActivityLog.action == action)
                .where(ReferralActivityLog.created_at >= cutoff)
            )
            return int(result.scalar() or 0)

    @staticmethod
    async def count_recent_user_rejoins(telegram_id: int, window_minutes: int) -> int:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=window_minutes)
        async with async_session() as session:
            result = await session.execute(
                select(func.count(ReferralActivityLog.id))
                .where(ReferralActivityLog.telegram_id == telegram_id)
                .where(ReferralActivityLog.action == "join")
                .where(ReferralActivityLog.is_rejoin.is_(True))
                .where(ReferralActivityLog.created_at >= cutoff)
            )
            return int(result.scalar() or 0)

    @staticmethod
    async def create_flag_if_new(
        flag_type: str,
        telegram_id: Optional[int],
        referral_link_id: Optional[int],
        details: str,
        cooldown_minutes: int = 30,
    ) -> bool:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=cooldown_minutes)
        async with async_session() as session:
            existing = await session.scalar(
                select(ReferralAbuseFlag.id)
                .where(ReferralAbuseFlag.flag_type == flag_type)
                .where(ReferralAbuseFlag.telegram_id == telegram_id)
                .where(ReferralAbuseFlag.referral_link_id == referral_link_id)
                .where(ReferralAbuseFlag.created_at >= cutoff)
            )
            if existing:
                return False

            session.add(
                ReferralAbuseFlag(
                    flag_type=flag_type,
                    telegram_id=telegram_id,
                    referral_link_id=referral_link_id,
                    details=details,
                )
            )
            await session.commit()
            return True
