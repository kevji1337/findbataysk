import asyncio
import importlib

import pytest


@pytest.fixture()
async def db_env(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("BOT_TOKEN", "test:token")
    monkeypatch.setenv("CHANNEL_ID", "-100123456")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    import bot.config
    import bot.database.models
    import bot.database.repository
    import bot.database.session
    import bot.services.referral_events

    importlib.reload(bot.config)
    importlib.reload(bot.database.models)
    importlib.reload(bot.database.repository)
    importlib.reload(bot.database.session)
    importlib.reload(bot.services.referral_events)

    from bot.database.models import init_db

    await init_db()

    yield


@pytest.mark.asyncio
async def test_referral_join_leave_no_double_count(db_env):
    from sqlalchemy import select

    from bot.database.models import ReferralLink, User
    from bot.database.session import get_session
    from bot.services.referral_events import handle_referral_join, handle_referral_leave

    async with get_session() as session:
        owner = User(telegram_id=100, username="owner", first_name="Owner")
        session.add(owner)
        await session.flush()
        link = ReferralLink(user_id=owner.id, invite_link="https://t.me/+test123")
        session.add(link)
        await session.flush()
        link_id = link.id

    owner_id, counted, _ = await handle_referral_join(
        invite_link="https://t.me/+test123",
        telegram_id=200,
    )
    assert owner_id == 100
    assert counted is True

    async with get_session() as session:
        link = await session.scalar(select(ReferralLink).where(ReferralLink.id == link_id))
        assert link.referral_count == 1

    owner_id, counted, _ = await handle_referral_join(
        invite_link="https://t.me/+test123",
        telegram_id=200,
    )
    assert owner_id == 100
    assert counted is False

    async with get_session() as session:
        link = await session.scalar(select(ReferralLink).where(ReferralLink.id == link_id))
        assert link.referral_count == 1

    referral_link_id, decremented = await handle_referral_leave(telegram_id=200)
    assert referral_link_id == link_id
    assert decremented is True

    async with get_session() as session:
        link = await session.scalar(select(ReferralLink).where(ReferralLink.id == link_id))
        assert link.referral_count == 0

    owner_id, counted, _ = await handle_referral_join(
        invite_link="https://t.me/+test123",
        telegram_id=200,
    )
    assert owner_id == 100
    assert counted is False

    referral_link_id, decremented = await handle_referral_leave(telegram_id=200)
    assert referral_link_id == link_id
    assert decremented is False


@pytest.mark.asyncio
async def test_referral_join_race_condition(db_env):
    from sqlalchemy import select

    from bot.database.models import ReferralLink, User
    from bot.database.session import get_session
    from bot.services.referral_events import handle_referral_join

    async with get_session() as session:
        owner = User(telegram_id=101, username="owner2", first_name="Owner2")
        session.add(owner)
        await session.flush()
        link = ReferralLink(user_id=owner.id, invite_link="https://t.me/+race123")
        session.add(link)
        await session.flush()
        link_id = link.id

    await asyncio.gather(
        handle_referral_join(invite_link="https://t.me/+race123", telegram_id=300),
        handle_referral_join(invite_link="https://t.me/+race123", telegram_id=300),
    )

    async with get_session() as session:
        link = await session.scalar(select(ReferralLink).where(ReferralLink.id == link_id))
        assert link.referral_count == 1


@pytest.mark.asyncio
async def test_referral_leave_race_condition(db_env):
    from sqlalchemy import select

    from bot.database.models import ReferralLink, User
    from bot.database.session import get_session
    from bot.services.referral_events import handle_referral_join, handle_referral_leave

    async with get_session() as session:
        owner = User(telegram_id=102, username="owner3", first_name="Owner3")
        session.add(owner)
        await session.flush()
        link = ReferralLink(user_id=owner.id, invite_link="https://t.me/+leave123")
        session.add(link)
        await session.flush()
        link_id = link.id

    await handle_referral_join(invite_link="https://t.me/+leave123", telegram_id=400)

    await asyncio.gather(
        handle_referral_leave(telegram_id=400),
        handle_referral_leave(telegram_id=400),
    )

    async with get_session() as session:
        link = await session.scalar(select(ReferralLink).where(ReferralLink.id == link_id))
        assert link.referral_count == 0


@pytest.mark.asyncio
async def test_leaderboard_realtime_updates_on_join_leave(db_env):
    from bot.database.models import ReferralLink, User
    from bot.database.repository import ReferralStatsRepository
    from bot.database.session import get_session
    from bot.services.referral_events import handle_referral_join, handle_referral_leave

    async with get_session() as session:
        owner = User(telegram_id=103, username="owner_lb", first_name="OwnerLB")
        session.add(owner)
        await session.flush()
        link = ReferralLink(user_id=owner.id, invite_link="https://t.me/+lb123")
        session.add(link)
        await session.flush()
        owner_tg_id = owner.telegram_id

    _, counted, _ = await handle_referral_join(invite_link="https://t.me/+lb123", telegram_id=777)
    assert counted is True

    rows_day = await ReferralStatsRepository.get_top_referrers_by_period(period="day", limit=10)
    assert len(rows_day) == 1
    assert rows_day[0][0].telegram_id == owner_tg_id
    assert rows_day[0][1] == 1

    rows_all = await ReferralStatsRepository.get_top_referrers_by_period(period="all", limit=10)
    assert len(rows_all) == 1
    assert rows_all[0][0].telegram_id == owner_tg_id
    assert rows_all[0][1] == 1

    _, decremented = await handle_referral_leave(telegram_id=777)
    assert decremented is True

    rows_day_after = await ReferralStatsRepository.get_top_referrers_by_period(period="day", limit=10)
    assert rows_day_after == []

    rows_all_after = await ReferralStatsRepository.get_top_referrers_by_period(period="all", limit=10)
    assert rows_all_after == []


@pytest.mark.asyncio
async def test_referral_second_round_via_another_link_is_not_counted(db_env):
    from sqlalchemy import select

    from bot.database.models import ReferralLink, User
    from bot.database.session import get_session
    from bot.services.referral_events import handle_referral_join, handle_referral_leave

    async with get_session() as session:
        owner_a = User(telegram_id=201, username="owner_a", first_name="OwnerA")
        owner_b = User(telegram_id=202, username="owner_b", first_name="OwnerB")
        session.add_all([owner_a, owner_b])
        await session.flush()

        link_a = ReferralLink(user_id=owner_a.id, invite_link="https://t.me/+ownerA")
        link_b = ReferralLink(user_id=owner_b.id, invite_link="https://t.me/+ownerB")
        session.add_all([link_a, link_b])
        await session.flush()

        link_a_id = link_a.id
        link_b_id = link_b.id

    # First join via owner A link must be counted.
    owner_id, counted, _ = await handle_referral_join(
        invite_link="https://t.me/+ownerA",
        telegram_id=999,
    )
    assert owner_id == 201
    assert counted is True

    # Leave resets active status and decrements counter once.
    referral_link_id, decremented = await handle_referral_leave(telegram_id=999)
    assert referral_link_id == link_a_id
    assert decremented is True

    # Re-join via another owner's link should NOT be counted (second round protection).
    owner_id_second, counted_second, _ = await handle_referral_join(
        invite_link="https://t.me/+ownerB",
        telegram_id=999,
    )
    assert owner_id_second == 202
    assert counted_second is False

    async with get_session() as session:
        link_a_row = await session.scalar(select(ReferralLink).where(ReferralLink.id == link_a_id))
        link_b_row = await session.scalar(select(ReferralLink).where(ReferralLink.id == link_b_id))
        assert link_a_row is not None
        assert link_b_row is not None
        assert link_a_row.referral_count == 0
        assert link_b_row.referral_count == 0
