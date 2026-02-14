from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    AdminActionLog,
    AdvertisingRequest,
    BroadcastJob,
    ReferralAbuseFlag,
    ReferralActivityLog,
    ReferralDailyStat,
    Referral,
    ReferralEvent,
    ReferralLink,
    User,
    async_session,
)


class UserRepository:
    """Р РµРїРѕР·РёС‚РѕСЂРёР№ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏРјРё."""

    @staticmethod
    async def get_or_create(
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> User:
        """РџРѕР»СѓС‡РёС‚СЊ РёР»Рё СЃРѕР·РґР°С‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ."""
        async with async_session() as session:
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
        """РџРѕР»СѓС‡РёС‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РїРѕ Telegram ID."""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(user_id: int) -> Optional[User]:
        """Получить пользователя по внутреннему ID."""
        async with async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def get_all_telegram_ids() -> list[int]:
        """Получить Telegram ID всех пользователей."""
        async with async_session() as session:
            result = await session.execute(select(User.telegram_id))
            return list(result.scalars().all())

    @staticmethod
    async def get_broadcast_telegram_ids() -> list[int]:
        """Получить пользователей для рассылки (исключая bot_blocked)."""
        async with async_session() as session:
            result = await session.execute(
                select(User.telegram_id).where(User.bot_blocked.is_(False))
            )
            return list(result.scalars().all())

    @staticmethod
    async def mark_bot_blocked(telegram_id: int) -> None:
        """Пометить пользователя как заблокировавшего бота."""
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(bot_blocked=True, blocked_at=datetime.now(UTC).replace(tzinfo=None))
            )
            await session.commit()


class ReferralRepository:
    """Р РµРїРѕР·РёС‚РѕСЂРёР№ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ СЂРµС„РµСЂР°Р»СЊРЅС‹РјРё СЃСЃС‹Р»РєР°РјРё."""

    @staticmethod
    async def create(user_id: int, invite_link: str) -> ReferralLink:
        """РЎРѕР·РґР°С‚СЊ СЂРµС„РµСЂР°Р»СЊРЅСѓСЋ СЃСЃС‹Р»РєСѓ."""
        async with async_session() as session:
            referral = ReferralLink(user_id=user_id, invite_link=invite_link)
            session.add(referral)
            await session.commit()
            await session.refresh(referral)
            return referral

    @staticmethod
    async def get_by_user_id(user_id: int) -> Optional[ReferralLink]:
        """РџРѕР»СѓС‡РёС‚СЊ СЂРµС„РµСЂР°Р»СЊРЅСѓСЋ СЃСЃС‹Р»РєСѓ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ."""
        async with async_session() as session:
            result = await session.execute(
                select(ReferralLink).where(ReferralLink.user_id == user_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def get_by_invite_link(invite_link: str) -> Optional[ReferralLink]:
        """РќР°Р№С‚Рё Р·Р°РїРёСЃСЊ РїРѕ СЃСЃС‹Р»РєРµ."""
        async with async_session() as session:
            result = await session.execute(
                select(ReferralLink).where(ReferralLink.invite_link == invite_link)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def increment_count(referral_id: int) -> None:
        """РЈРІРµР»РёС‡РёС‚СЊ СЃС‡С‘С‚С‡РёРє СЂРµС„РµСЂР°Р»РѕРІ."""
        async with async_session() as session:
            await session.execute(
                update(ReferralLink)
                .where(ReferralLink.id == referral_id)
                .values(referral_count=ReferralLink.referral_count + 1)
            )
            await session.commit()

    @staticmethod
    async def decrement_count(referral_id: int) -> None:
        """РЈРјРµРЅСЊС€РёС‚СЊ СЃС‡С‘С‚С‡РёРє СЂРµС„РµСЂР°Р»РѕРІ (РїСЂРё РІС‹С…РѕРґРµ)."""
        async with async_session() as session:
            await session.execute(
                update(ReferralLink)
                .where(ReferralLink.id == referral_id)
                .where(ReferralLink.referral_count > 0)  # РќРµ СѓС…РѕРґРёС‚СЊ РІ РјРёРЅСѓСЃ
                .values(referral_count=ReferralLink.referral_count - 1)
            )
            await session.commit()

    @staticmethod
    async def get_user_by_invite_link(invite_link: str) -> Optional[User]:
        """РџРѕР»СѓС‡РёС‚СЊ РІР»Р°РґРµР»СЊС†Р° СЃСЃС‹Р»РєРё."""
        async with async_session() as session:
            result = await session.execute(
                select(User)
                .join(ReferralLink)
                .where(ReferralLink.invite_link == invite_link)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def claim_gift(referral_id: int, count: int = 1) -> None:
        """РЈРІРµР»РёС‡РёС‚СЊ СЃС‡С‘С‚С‡РёРє РїРѕР»СѓС‡РµРЅРЅС‹С… РїРѕРґР°СЂРєРѕРІ."""
        async with async_session() as session:
            await session.execute(
                update(ReferralLink)
                .where(ReferralLink.id == referral_id)
                .values(gifts_claimed=ReferralLink.gifts_claimed + count)
            )
            await session.commit()

    @staticmethod
    async def claim_available_gifts(
        referral_id: int,
        referrals_per_gift: int,
    ) -> int:
        """
        РђС‚РѕРјР°СЂРЅРѕ Р·Р°С„РёРєСЃРёСЂРѕРІР°С‚СЊ РІСЃРµ РґРѕСЃС‚СѓРїРЅС‹Рµ Рє РІС‹РґР°С‡Рµ РїРѕРґР°СЂРєРё.

        Р’РѕР·РІСЂР°С‰Р°РµС‚ РєРѕР»РёС‡РµСЃС‚РІРѕ СЂРµР°Р»СЊРЅРѕ Р·Р°С„РёРєСЃРёСЂРѕРІР°РЅРЅС‹С… РїРѕРґР°СЂРєРѕРІ.
        """
        if referrals_per_gift <= 0:
            return 0

        async with async_session() as session:
            # Optimistic locking РїРѕ gifts_claimed:
            # РµСЃР»Рё РїР°СЂР°Р»Р»РµР»СЊРЅС‹Р№ Р·Р°РїСЂРѕСЃ СѓР¶Рµ РІС‹РґР°Р» РїРѕРґР°СЂРєРё, UPDATE РЅРµ РїСЂРѕР№РґРµС‚.
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
        """Р”РѕР±Р°РІРёС‚СЊ Р·Р°РїРёСЃСЊ Рѕ СЂРµС„РµСЂР°Р»Рµ."""
        async with async_session() as session:
            # РџСЂРѕРІРµСЂСЏРµРј, РЅРµ Р±С‹Р» Р»Рё СѓР¶Рµ РґРѕР±Р°РІР»РµРЅ
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
        РЈРґР°Р»РёС‚СЊ Р·Р°РїРёСЃСЊ Рѕ СЂРµС„РµСЂР°Р»Рµ (РїСЂРё РІС‹С…РѕРґРµ РёР· РєР°РЅР°Р»Р°).
        Р’РѕР·РІСЂР°С‰Р°РµС‚ ID СЂРµС„РµСЂР°Р»СЊРЅРѕР№ СЃСЃС‹Р»РєРё, РµСЃР»Рё Р±С‹Р» РЅР°Р№РґРµРЅ Рё СѓРґР°Р»С‘РЅ.
        """
        async with async_session() as session:
            # РќР°С…РѕРґРёРј Р·Р°РїРёСЃСЊ
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


class AdvertisingRepository:
    """Р РµРїРѕР·РёС‚РѕСЂРёР№ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ Р·Р°СЏРІРєР°РјРё РЅР° СЂРµРєР»Р°РјСѓ."""

    @staticmethod
    async def create(user_id: int, channel_link: str) -> AdvertisingRequest:
        """РЎРѕР·РґР°С‚СЊ Р·Р°СЏРІРєСѓ РЅР° СЂРµРєР»Р°РјСѓ."""
        async with async_session() as session:
            request = AdvertisingRequest(user_id=user_id, channel_link=channel_link)
            session.add(request)
            await session.commit()
            await session.refresh(request)
            return request

    @staticmethod
    async def get_by_id(request_id: int) -> Optional[AdvertisingRequest]:
        """РџРѕР»СѓС‡РёС‚СЊ Р·Р°СЏРІРєСѓ РїРѕ ID."""
        async with async_session() as session:
            result = await session.execute(
                select(AdvertisingRequest).where(AdvertisingRequest.id == request_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def update_status(request_id: int, status: str) -> bool:
        """
        РћР±РЅРѕРІРёС‚СЊ СЃС‚Р°С‚СѓСЃ Р·Р°СЏРІРєРё С‚РѕР»СЊРєРѕ РµСЃР»Рё РѕРЅР° РµС‰С‘ pending.

        Р’РѕР·РІСЂР°С‰Р°РµС‚ True, РµСЃР»Рё СЃС‚Р°С‚СѓСЃ СЂРµР°Р»СЊРЅРѕ РёР·РјРµРЅС‘РЅ.
        """
        async with async_session() as session:
            result = await session.execute(
                update(AdvertisingRequest)
                .where(AdvertisingRequest.id == request_id)
                .where(AdvertisingRequest.status == "pending")
                .values(
                    status=status,
                    # Column is TIMESTAMP WITHOUT TIME ZONE; store naive UTC.
                    reviewed_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            await session.commit()
            return bool(result.rowcount and result.rowcount > 0)

    @staticmethod
    async def get_all_requests(
        limit: int = 20,
        status_filter: Optional[str] = None
    ) -> list[tuple[AdvertisingRequest, User]]:
        """РџРѕР»СѓС‡РёС‚СЊ РёСЃС‚РѕСЂРёСЋ Р·Р°СЏРІРѕРє СЃ РёРЅС„РѕСЂРјР°С†РёРµР№ Рѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏС…."""
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
        """РџРѕР»СѓС‡РёС‚СЊ РєРѕР»РёС‡РµСЃС‚РІРѕ РѕР¶РёРґР°СЋС‰РёС… Р·Р°СЏРІРѕРє."""
        async with async_session() as session:
            from sqlalchemy import func
            result = await session.execute(
                select(func.count(AdvertisingRequest.id))
                .where(AdvertisingRequest.status == "pending")
            )
            return result.scalar() or 0

    @staticmethod
    async def get_user_requests_count(user_id: int, hours: int = 1) -> int:
        """РџРѕР»СѓС‡РёС‚СЊ РєРѕР»РёС‡РµСЃС‚РІРѕ Р·Р°СЏРІРѕРє РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ Р·Р° РїРѕСЃР»РµРґРЅРёРµ N С‡Р°СЃРѕРІ."""
        async with async_session() as session:
            from sqlalchemy import func
            from datetime import timedelta
            
            cutoff = datetime.now(UTC) - timedelta(hours=hours)
            result = await session.execute(
                select(func.count(AdvertisingRequest.id))
                .where(AdvertisingRequest.user_id == user_id)
                .where(AdvertisingRequest.created_at >= cutoff)
            )
            return result.scalar() or 0


class ReferralStatsRepository:
    """Р РµРїРѕР·РёС‚РѕСЂРёР№ РґР»СЏ СЃС‚Р°С‚РёСЃС‚РёРєРё СЂРµС„РµСЂР°Р»РѕРІ."""

    @staticmethod
    async def get_top_referrers(limit: int = 10) -> list[tuple[User, int]]:
        """РџРѕР»СѓС‡РёС‚СЊ С‚РѕРї РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№ РїРѕ РєРѕР»РёС‡РµСЃС‚РІСѓ СЂРµС„РµСЂР°Р»РѕРІ."""
        async with async_session() as session:
            from sqlalchemy import func

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
        РўРѕРї СЂРµС„РµСЂРµСЂРѕРІ Р·Р° РїРµСЂРёРѕРґ.

        period:
            - "all"   вЂ” РІСЃС‘ РІСЂРµРјСЏ (РёСЃРїРѕР»СЊР·СѓРµС‚ ReferralLink.referral_count)
            - "day"   вЂ” РїРѕСЃР»РµРґРЅРёРµ 24 С‡Р°СЃР°
            - "week"  вЂ” РїРѕСЃР»РµРґРЅРёРµ 7 РґРЅРµР№
            - "month" вЂ” РїРѕСЃР»РµРґРЅРёРµ 30 РґРЅРµР№

        Р”Р»СЏ РїРµСЂРёРѕРґРѕРІ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ С‚Р°Р±Р»РёС†Р° ReferralEvent:
        СЃС‡РёС‚Р°РµРј С‚РѕР»СЊРєРѕ СЃРѕР±С‹С‚РёСЏ СЃ is_counted = True, С‡С‚РѕР±С‹ РєРѕСЂСЂРµРєС‚РЅРѕ
        СѓС‡РёС‚С‹РІР°С‚СЊ РѕС‚РїРёСЃРєРё (РІС‹С‡С‚РµРЅРЅС‹Рµ СЂРµС„РµСЂР°Р»С‹ РЅРµ РїРѕРїР°РґР°СЋС‚ РІ С‚РѕРї).
        """
        period = period or "all"
        period = period.lower()

        if period == "all":
            # Р”Р»СЏ РІСЃРµРіРѕ РІСЂРµРјРµРЅРё РґРѕСЃС‚Р°С‚РѕС‡РЅРѕ Р°РіСЂРµРіР°С‚Р° РїРѕ ReferralLink
            return await ReferralStatsRepository.get_top_referrers(limit=limit)

        now = datetime.now(UTC)
        if period == "day":
            since = now - timedelta(days=1)
        elif period == "week":
            since = now - timedelta(days=7)
        elif period == "month":
            since = now - timedelta(days=30)
        else:
            # РќРµРёР·РІРµСЃС‚РЅС‹Р№ РїРµСЂРёРѕРґ вЂ” fallback Рє "all time"
            return await ReferralStatsRepository.get_top_referrers(limit=limit)

        async with async_session() as session:
            from sqlalchemy import func

            # Р‘С‹СЃС‚СЂС‹Р№ РїСѓС‚СЊ: РґРЅРµРІРЅС‹Рµ РїСЂРµРґР°РіСЂРµРіР°С†РёРё (РѕР±РЅРѕРІР»СЏСЋС‚СЃСЏ РІ real-time РЅР° join/leave).
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

            # Fallback РґР»СЏ СЃС‚Р°СЂС‹С… РґР°РЅРЅС‹С… (РµСЃР»Рё РїСЂРµРґР°РіСЂРµРіР°С†РёРё РµС‰С‘ РЅРµ Р·Р°РїРѕР»РЅРµРЅС‹):
            # СЃС‡РёС‚Р°РµРј РїРѕ ReferralEvent.
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
        """РџРѕР»СѓС‡РёС‚СЊ РѕР±С‰СѓСЋ СЃС‚Р°С‚РёСЃС‚РёРєСѓ РїРѕ СЂРµС„РµСЂР°Р»Р°Рј."""
        async with async_session() as session:
            from sqlalchemy import func
            
            # Р’СЃРµРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№
            users_count = await session.execute(select(func.count(User.id)))
            users_count = users_count.scalar() or 0
            
            # Р’СЃРµРіРѕ СЃСЃС‹Р»РѕРє
            links_count = await session.execute(select(func.count(ReferralLink.id)))
            links_count = links_count.scalar() or 0
            
            # Р’СЃРµРіРѕ РїРµСЂРµС…РѕРґРѕРІ
            total_referrals = await session.execute(
                select(func.sum(ReferralLink.referral_count))
            )
            total_referrals = total_referrals.scalar() or 0
            
            return {
                "users_count": users_count,
                "links_count": links_count,
                "total_referrals": total_referrals,
            }


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


class AdminActionLogRepository:
    """Р РµРїРѕР·РёС‚РѕСЂРёР№ РґР»СЏ Р¶СѓСЂРЅР°Р»Р° РґРµР№СЃС‚РІРёР№ Р°РґРјРёРЅРѕРІ."""

    @staticmethod
    async def create(
        admin_telegram_id: int,
        action_type: str,
        target_type: str,
        target_id: int,
        details: Optional[str] = None,
    ) -> AdminActionLog:
        """Р—Р°РїРёСЃР°С‚СЊ СЃРѕР±С‹С‚РёРµ РІ Р¶СѓСЂРЅР°Р»."""
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
        """РџРѕР»СѓС‡РёС‚СЊ РїРѕСЃР»РµРґРЅРёРµ СЃРѕР±С‹С‚РёСЏ Р¶СѓСЂРЅР°Р»Р°."""
        async with async_session() as session:
            result = await session.execute(
                select(AdminActionLog)
                .order_by(AdminActionLog.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())


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
        async with async_session() as session:
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
        async with async_session() as session:
            result = await session.execute(select(BroadcastJob).where(BroadcastJob.id == job_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def acquire_next_pending() -> Optional[BroadcastJob]:
        """Взять ближайшую pending-задачу и перевести в processing."""
        async with async_session() as session:
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
        async with async_session() as session:
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
        async with async_session() as session:
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
        async with async_session() as session:
            job = await session.scalar(select(BroadcastJob).where(BroadcastJob.id == job_id))
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
