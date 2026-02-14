"""
Тесты для публичного лидерборда (ReferralStatsRepository.get_top_referrers_by_period).

Проверяем:
- корректный расчёт "всё время" (all);
- фильтры по периодам (day/week/month);
- исключение отписавшихся (is_counted = False).
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select


@pytest.fixture()
async def leaderboard_db_env(tmp_path, monkeypatch):
    """
    Отдельное окружение БД для тестов лидерборда (SQLite в файле).

    Не трогаем продакшен/Postgres, тесты изолированы.
    """
    db_path = tmp_path / "lb_test.db"
    monkeypatch.setenv("BOT_TOKEN", "test:token")
    monkeypatch.setenv("CHANNEL_ID", "-100123456")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    import importlib

    import bot.config
    import bot.database.models
    import bot.database.repository
    import bot.database.session

    importlib.reload(bot.config)
    importlib.reload(bot.database.models)
    importlib.reload(bot.database.session)
    importlib.reload(bot.database.repository)

    from bot.database.models import init_db

    await init_db()

    yield


@pytest.mark.asyncio
async def test_leaderboard_all_time(leaderboard_db_env):
    """Топ за всё время использует ReferralLink.referral_count."""
    from bot.database.models import ReferralLink, User
    from bot.database.session import get_session
    from bot.database.repository import ReferralStatsRepository

    async with get_session() as session:
        u1 = User(telegram_id=1, username="user1", first_name="User1")
        u2 = User(telegram_id=2, username="user2", first_name="User2")
        session.add_all([u1, u2])
        await session.flush()

        l1 = ReferralLink(user_id=u1.id, invite_link="https://t.me/+u1")
        l2 = ReferralLink(user_id=u2.id, invite_link="https://t.me/+u2")
        l1.referral_count = 5
        l2.referral_count = 10
        session.add_all([l1, l2])
        await session.commit()

    rows = await ReferralStatsRepository.get_top_referrers_by_period(period="all", limit=10)

    # Ожидаем, что на первом месте u2 (10), на втором u1 (5)
    assert len(rows) == 2
    (user_top, total_top), (user_second, total_second) = rows
    assert user_top.telegram_id == 2
    assert total_top == 10
    assert user_second.telegram_id == 1
    assert total_second == 5


@pytest.mark.asyncio
async def test_leaderboard_period_filters_respect_is_counted(leaderboard_db_env):
    """
    Для периодов day/week/month считаем только ReferralEvent с is_counted = True
    и first_join_at в нужном диапазоне.
    """
    from sqlalchemy import func

    from bot.database.models import ReferralEvent, ReferralLink, User
    from bot.database.session import get_session
    from bot.database.repository import ReferralStatsRepository

    now = datetime.now(timezone.utc)

    async with get_session() as session:
        u1 = User(telegram_id=11, username="u1", first_name="U1")
        u2 = User(telegram_id=22, username="u2", first_name="U2")
        session.add_all([u1, u2])
        await session.flush()

        l1 = ReferralLink(user_id=u1.id, invite_link="https://t.me/+u1p")
        l2 = ReferralLink(user_id=u2.id, invite_link="https://t.me/+u2p")
        session.add_all([l1, l2])
        await session.flush()

        # u1: 2 актуальных реферала за последний день
        e1 = ReferralEvent(
            referral_link_id=l1.id,
            telegram_id=1001,
            first_join_at=now - timedelta(hours=1),
            is_counted=True,
            status="joined",
        )
        e2 = ReferralEvent(
            referral_link_id=l1.id,
            telegram_id=1002,
            first_join_at=now - timedelta(hours=2),
            is_counted=True,
            status="joined",
        )

        # u2: 1 реферал, но отписался (is_counted=False)
        e3 = ReferralEvent(
            referral_link_id=l2.id,
            telegram_id=2001,
            first_join_at=now - timedelta(hours=3),
            is_counted=False,
            status="left",
        )

        session.add_all([e1, e2, e3])
        await session.commit()

        # sanity-check: в таблице 3 события
        count_events = await session.scalar(select(func.count(ReferralEvent.id)))
        assert count_events == 3

    # Для периода "day" u1 должен быть в топе с total=2, u2 не должен попасть
    rows_day = await ReferralStatsRepository.get_top_referrers_by_period(
        period="day",
        limit=10,
    )
    assert len(rows_day) == 1
    user_day, total_day = rows_day[0]
    assert user_day.telegram_id == 11
    assert total_day == 2

    # Для "week" и "month" результат должен быть таким же (все first_join_at свежие)
    rows_week = await ReferralStatsRepository.get_top_referrers_by_period(
        period="week",
        limit=10,
    )
    rows_month = await ReferralStatsRepository.get_top_referrers_by_period(
        period="month",
        limit=10,
    )

    assert [(u.telegram_id, t) for u, t in rows_week] == [(11, 2)]
    assert [(u.telegram_id, t) for u, t in rows_month] == [(11, 2)]


@pytest.mark.asyncio
async def test_leaderboard_unknown_period_falls_back_to_all(leaderboard_db_env):
    """Неизвестный period ведёт себя как 'all'."""
    from bot.database.models import ReferralLink, User
    from bot.database.session import get_session
    from bot.database.repository import ReferralStatsRepository

    async with get_session() as session:
        u1 = User(telegram_id=111, username=None, first_name="Name1")
        session.add(u1)
        await session.flush()

        l1 = ReferralLink(user_id=u1.id, invite_link="https://t.me/+x1")
        l1.referral_count = 3
        session.add(l1)
        await session.commit()

    rows_custom = await ReferralStatsRepository.get_top_referrers_by_period(
        period="unknown",
        limit=10,
    )
    assert len(rows_custom) == 1
    user, total = rows_custom[0]
    assert user.telegram_id == 111
    assert total == 3

