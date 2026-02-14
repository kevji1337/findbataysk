import importlib

import pytest


@pytest.fixture()
async def db_env(tmp_path, monkeypatch):
    db_path = tmp_path / "admin_logs_test.db"
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
async def test_admin_action_log_create_and_read(db_env):
    from bot.database.repository import AdminActionLogRepository

    created = await AdminActionLogRepository.create(
        admin_telegram_id=111,
        action_type="ad_approve",
        target_type="advertising_request",
        target_id=42,
        details="user_id=777",
    )
    assert created.id > 0

    logs = await AdminActionLogRepository.get_recent(limit=10)
    assert len(logs) == 1
    assert logs[0].admin_telegram_id == 111
    assert logs[0].action_type == "ad_approve"
    assert logs[0].target_type == "advertising_request"
    assert logs[0].target_id == 42
    assert logs[0].details == "user_id=777"
