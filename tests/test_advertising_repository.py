import importlib

import pytest


@pytest.fixture()
async def db_env(tmp_path, monkeypatch):
    db_path = tmp_path / "ads_test.db"
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
async def test_update_status_changes_only_pending(db_env):
    from bot.database.models import AdvertisingRequest, User
    from bot.database.repository import AdvertisingRepository
    from bot.database.session import get_session

    async with get_session() as session:
        user = User(telegram_id=500, username="u500", first_name="U500")
        session.add(user)
        await session.flush()
        req = AdvertisingRequest(user_id=user.id, channel_link="https://t.me/u500")
        session.add(req)
        await session.flush()
        req_id = req.id

    first = await AdvertisingRepository.update_status(req_id, "approved")
    second = await AdvertisingRepository.update_status(req_id, "rejected")

    assert first is True
    assert second is False

    async with get_session() as session:
        row = await session.get(AdvertisingRequest, req_id)
        assert row is not None
        assert row.status == "approved"
        assert row.reviewed_at is not None
