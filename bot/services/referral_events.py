"""РўСЂР°РЅР·Р°РєС†РёРѕРЅРЅР°СЏ Р»РѕРіРёРєР° СѓС‡С‘С‚Р° СЂРµС„РµСЂР°Р»РѕРІ."""

from datetime import UTC, datetime
from typing import Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from bot.database.models import (
    ReferralActivityLog,
    ReferralDailyStat,
    ReferralEvent,
    ReferralLink,
    User,
)
from bot.database.session import get_session
from bot.services.leaderboard_cache import invalidate_leaderboard_cache


async def _increment_daily_stat(
    *,
    session,
    owner_user_id: int,
    stat_date,
) -> None:
    insert_stmt = (
        pg_insert(ReferralDailyStat)
        .values(
            owner_user_id=owner_user_id,
            stat_date=stat_date,
            active_referrals=0,
        )
        .on_conflict_do_nothing(index_elements=["owner_user_id", "stat_date"])
    )
    await session.execute(insert_stmt)
    await session.execute(
        update(ReferralDailyStat)
        .where(ReferralDailyStat.owner_user_id == owner_user_id)
        .where(ReferralDailyStat.stat_date == stat_date)
        .values(active_referrals=ReferralDailyStat.active_referrals + 1)
    )


async def _decrement_daily_stat(
    *,
    session,
    owner_user_id: int,
    stat_date,
) -> None:
    await session.execute(
        update(ReferralDailyStat)
        .where(ReferralDailyStat.owner_user_id == owner_user_id)
        .where(ReferralDailyStat.stat_date == stat_date)
        .where(ReferralDailyStat.active_referrals > 0)
        .values(active_referrals=ReferralDailyStat.active_referrals - 1)
    )


def _log_activity(
    *,
    session,
    telegram_id: int,
    referral_link_id: int,
    action: str,
    is_rejoin: bool = False,
) -> None:
    session.add(
        ReferralActivityLog(
            telegram_id=telegram_id,
            referral_link_id=referral_link_id,
            action=action,
            is_rejoin=is_rejoin,
        )
    )


async def handle_referral_join(
    invite_link: str,
    telegram_id: int,
) -> Tuple[Optional[int], bool, Optional[int]]:
    """
    Обработать вступление по реферальной ссылке.

    Returns:
        (owner_telegram_id, counted, referral_link_id)
    """
    async with get_session() as session:
        referral_link = await session.scalar(
            select(ReferralLink).where(ReferralLink.invite_link == invite_link)
        )
        if not referral_link:
            return None, False, None

        now = datetime.now(UTC)
        counted = False

        insert_stmt = (
            pg_insert(ReferralEvent)
            .values(
                referral_link_id=referral_link.id,
                telegram_id=telegram_id,
                last_join_at=now,
                status="joined",
                is_counted=True,
            )
            .on_conflict_do_nothing(index_elements=["telegram_id"])
        )
        result = await session.execute(insert_stmt)

        if result.rowcount and result.rowcount > 0:
            await session.execute(
                update(ReferralLink)
                .where(ReferralLink.id == referral_link.id)
                .values(referral_count=ReferralLink.referral_count + 1)
            )
            _log_activity(
                session=session,
                telegram_id=telegram_id,
                referral_link_id=referral_link.id,
                action="join",
                is_rejoin=False,
            )
            await _increment_daily_stat(
                session=session,
                owner_user_id=referral_link.user_id,
                stat_date=now.date(),
            )
            counted = True
            invalidate_leaderboard_cache()
        else:
            event = await session.scalar(
                select(ReferralEvent).where(ReferralEvent.telegram_id == telegram_id)
            )
            if event:
                await session.execute(
                    update(ReferralEvent)
                    .where(ReferralEvent.id == event.id)
                    .values(last_join_at=now, status="joined")
                )
                _log_activity(
                    session=session,
                    telegram_id=telegram_id,
                    referral_link_id=event.referral_link_id,
                    action="join",
                    is_rejoin=True,
                )

        owner_telegram_id = await session.scalar(
            select(User.telegram_id).where(User.id == referral_link.user_id)
        )

        return owner_telegram_id, counted, referral_link.id


async def handle_referral_leave(telegram_id: int) -> Tuple[Optional[int], bool]:
    """
    Обработать выход реферала из канала.

    Returns:
        (referral_link_id, decremented)
    """
    async with get_session() as session:
        now = datetime.now(UTC)
        # 1) Основной кейс: активный counted-реферал уходит.
        #    Обновляем событие атомарно; только один конкурентный вызов сможет пройти.
        counted_result = await session.execute(
            update(ReferralEvent)
            .where(ReferralEvent.telegram_id == telegram_id)
            .where(ReferralEvent.status != "left")
            .where(ReferralEvent.is_counted.is_(True))
            .values(left_at=now, status="left", is_counted=False)
            .returning(
                ReferralEvent.referral_link_id,
                ReferralEvent.first_join_at,
            )
        )
        counted_row = counted_result.first()
        if counted_row:
            referral_link_id, first_join_at = counted_row
            owner_user_id = await session.scalar(
                select(ReferralLink.user_id).where(ReferralLink.id == referral_link_id)
            )
            await session.execute(
                update(ReferralLink)
                .where(ReferralLink.id == referral_link_id)
                .where(ReferralLink.referral_count > 0)
                .values(referral_count=ReferralLink.referral_count - 1)
            )
            if owner_user_id and first_join_at:
                await _decrement_daily_stat(
                    session=session,
                    owner_user_id=owner_user_id,
                    stat_date=first_join_at.date(),
                )
            _log_activity(
                session=session,
                telegram_id=telegram_id,
                referral_link_id=referral_link_id,
                action="leave",
            )
            invalidate_leaderboard_cache()
            return referral_link_id, True

        # 2) Событие есть, но не должно уменьшать счетчик (уже было вычтено ранее).
        not_counted_result = await session.execute(
            update(ReferralEvent)
            .where(ReferralEvent.telegram_id == telegram_id)
            .where(ReferralEvent.status != "left")
            .where(ReferralEvent.is_counted.is_(False))
            .values(left_at=now, status="left", is_counted=False)
            .returning(ReferralEvent.referral_link_id)
        )
        not_counted_row = not_counted_result.first()
        if not_counted_row:
            _log_activity(
                session=session,
                telegram_id=telegram_id,
                referral_link_id=not_counted_row[0],
                action="leave",
            )
            return not_counted_row[0], False

        # 3) Ничего не обновили: события нет или оно уже в статусе left.
        existing_link_id = await session.scalar(
            select(ReferralEvent.referral_link_id).where(
                ReferralEvent.telegram_id == telegram_id
            )
        )
        return existing_link_id, False
