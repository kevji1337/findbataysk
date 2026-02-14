import asyncio
import importlib

import pytest


@pytest.fixture()
async def db_env(tmp_path, monkeypatch):
    db_path = tmp_path / "claim_test.db"
    monkeypatch.setenv("BOT_TOKEN", "test:token")
    monkeypatch.setenv("CHANNEL_ID", "-100123456")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

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
async def test_claim_available_gifts_is_concurrent_safe(db_env):
    from sqlalchemy import select

    from bot.database.models import ReferralLink, User
    from bot.database.repository import ReferralRepository
    from bot.database.session import get_session

    async with get_session() as session:
        owner = User(telegram_id=700, username="owner700", first_name="Owner700")
        session.add(owner)
        await session.flush()
        link = ReferralLink(
            user_id=owner.id,
            invite_link="https://t.me/+claim700",
            referral_count=12,
            gifts_claimed=0,
        )
        session.add(link)
        await session.flush()
        link_id = link.id

    results = await asyncio.gather(
        ReferralRepository.claim_available_gifts(
            referral_id=link_id,
            referrals_per_gift=5,
        ),
        ReferralRepository.claim_available_gifts(
            referral_id=link_id,
            referrals_per_gift=5,
        ),
    )

    assert sum(results) == 2
    assert sorted(results) in ([0, 2], [1, 1])

    async with get_session() as session:
        row = await session.scalar(select(ReferralLink).where(ReferralLink.id == link_id))
        assert row is not None
        assert row.gifts_claimed == 2
