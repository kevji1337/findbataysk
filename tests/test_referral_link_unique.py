import importlib

import pytest


@pytest.fixture()
async def db_env(tmp_path, monkeypatch):
    db_path = tmp_path / "referral_unique.db"
    monkeypatch.setenv("BOT_TOKEN", "test:token")
    monkeypatch.setenv("CHANNEL_ID", "-100123456")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    import bot.config
    import bot.database.models
    import bot.database.repository

    importlib.reload(bot.config)
    importlib.reload(bot.database.models)
    importlib.reload(bot.database.repository)

    from bot.database.models import init_db

    await init_db()
    yield


@pytest.mark.asyncio
async def test_create_or_get_by_user_id_is_idempotent(db_env):
    from bot.database.models import User
    from bot.database.repository import ReferralRepository
    from bot.database.session import get_session

    async with get_session() as session:
        owner = User(telegram_id=501, username="owner501", first_name="Owner501")
        session.add(owner)
        await session.flush()
        owner_id = owner.id

    first_link, created_first = await ReferralRepository.create_or_get_by_user_id(
        user_id=owner_id,
        invite_link="https://t.me/+first501",
    )
    second_link, created_second = await ReferralRepository.create_or_get_by_user_id(
        user_id=owner_id,
        invite_link="https://t.me/+second501",
    )

    assert created_first is True
    assert created_second is False
    assert first_link.id == second_link.id
    assert second_link.invite_link == "https://t.me/+first501"
