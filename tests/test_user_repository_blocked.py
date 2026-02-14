import importlib

import pytest


@pytest.fixture()
async def db_env(tmp_path, monkeypatch):
    db_path = tmp_path / "users_blocked_test.db"
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
async def test_broadcast_targets_exclude_blocked_users(db_env):
    from bot.database.models import User
    from bot.database.repository import UserRepository
    from bot.database.session import get_session

    async with get_session() as session:
        session.add_all(
            [
                User(telegram_id=1001, username="u1", first_name="U1"),
                User(telegram_id=1002, username="u2", first_name="U2"),
            ]
        )

    await UserRepository.mark_bot_blocked(telegram_id=1002)
    targets = await UserRepository.get_broadcast_telegram_ids()
    assert 1001 in targets
    assert 1002 not in targets

    # If user interacts again, he should be auto-unblocked.
    await UserRepository.get_or_create(telegram_id=1002, username="u2", first_name="U2")
    targets_after_return = await UserRepository.get_broadcast_telegram_ids()
    assert 1002 in targets_after_return
