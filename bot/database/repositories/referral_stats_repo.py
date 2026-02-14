"""Репозиторий для статистики рефералов."""

from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select

from bot.database.models import (
    ReferralDailyStat,
    ReferralEvent,
    ReferralLink,
    User,
    async_session,
)


class ReferralStatsRepository:
    """Репозиторий для статистики рефералов."""

    @staticmethod
    async def get_top_referrers(limit: int = 10) -> list[tuple[User, int]]:
        """Получить топ пользователей по количеству рефералов."""
        async with async_session() as session:
            totals_subq = (
                select(
                    ReferralLink.user_id.label("user_id"),
                    func.sum(ReferralLink.referral_count).label("total"),
                )
                .group_by(ReferralLink.user_id)
                .having(func.sum(ReferralLink.referral_count) > 0)
                .order_by(func.sum(ReferralLink.referral_count).desc())
                .limit(limit)
                .subquery()
            )

            result = await session.execute(
                select(User, totals_subq.c.total)
                .join(totals_subq, totals_subq.c.user_id == User.id)
                .order_by(totals_subq.c.total.desc())
            )
            return result.all()

    @staticmethod
    async def get_top_referrers_by_period(
        period: str = "all",
        limit: int = 10,
    ) -> list[tuple[User, int]]:
        """
        Топ рефереров за период.

        period:
            - "all"   — всё время (использует ReferralLink.referral_count)
            - "day"   — последние 24 часа
            - "week"  — последние 7 дней
            - "month" — последние 30 дней
        """
        period = (period or "all").lower()

        if period == "all":
            return await ReferralStatsRepository.get_top_referrers(limit=limit)

        now = datetime.now(UTC).replace(tzinfo=None)
        if period == "day":
            since = now - timedelta(days=1)
        elif period == "week":
            since = now - timedelta(days=7)
        elif period == "month":
            since = now - timedelta(days=30)
        else:
            return await ReferralStatsRepository.get_top_referrers(limit=limit)

        async with async_session() as session:
            # Быстрый путь: дневные предагрегации
            period_subq = (
                select(
                    ReferralDailyStat.owner_user_id.label("user_id"),
                    func.sum(ReferralDailyStat.active_referrals).label("total"),
                )
                .where(ReferralDailyStat.stat_date >= since.date())
                .where(ReferralDailyStat.active_referrals > 0)
                .group_by(ReferralDailyStat.owner_user_id)
                .having(func.sum(ReferralDailyStat.active_referrals) > 0)
                .order_by(func.sum(ReferralDailyStat.active_referrals).desc())
                .limit(limit)
                .subquery()
            )
            result = await session.execute(
                select(User, period_subq.c.total)
                .join(period_subq, period_subq.c.user_id == User.id)
                .order_by(period_subq.c.total.desc())
            )
            rows = result.all()
            if rows:
                return rows

            # Fallback: считаем по ReferralEvent
            fallback_subq = (
                select(
                    ReferralLink.user_id.label("user_id"),
                    func.count(ReferralEvent.id).label("total"),
                )
                .join(
                    ReferralEvent,
                    ReferralEvent.referral_link_id == ReferralLink.id,
                )
                .where(ReferralEvent.is_counted.is_(True))
                .where(ReferralEvent.first_join_at >= since)
                .group_by(ReferralLink.user_id)
                .having(func.count(ReferralEvent.id) > 0)
                .order_by(func.count(ReferralEvent.id).desc())
                .limit(limit)
                .subquery()
            )
            fallback_result = await session.execute(
                select(User, fallback_subq.c.total)
                .join(fallback_subq, fallback_subq.c.user_id == User.id)
                .order_by(fallback_subq.c.total.desc())
            )
            return fallback_result.all()

    @staticmethod
    async def get_total_stats() -> dict:
        """Получить общую статистику по рефералам."""
        async with async_session() as session:
            users_count = await session.execute(select(func.count(User.id)))
            users_count = users_count.scalar() or 0

            links_count = await session.execute(select(func.count(ReferralLink.id)))
            links_count = links_count.scalar() or 0

            total_referrals = await session.execute(
                select(func.sum(ReferralLink.referral_count))
            )
            total_referrals = total_referrals.scalar() or 0

            return {
                "users_count": users_count,
                "links_count": links_count,
                "total_referrals": total_referrals,
            }
