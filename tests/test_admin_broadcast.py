from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers import admin as admin_handler


@pytest.mark.asyncio
async def test_admin_broadcast_send_rejects_non_admin(monkeypatch):
    monkeypatch.setattr(type(admin_handler.settings), "is_admin", lambda _self, _uid: False)

    clear = AsyncMock()
    state = SimpleNamespace(clear=clear)

    answer = AsyncMock()
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=111),
        chat=SimpleNamespace(id=111),
        message_id=10,
        answer=answer,
    )
    bot = SimpleNamespace(copy_message=AsyncMock())

    await admin_handler.admin_broadcast_send(message=message, state=state, bot=bot)

    clear.assert_awaited_once()
    bot.copy_message.assert_not_called()
    answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_broadcast_send_handles_empty_user_list(monkeypatch):
    monkeypatch.setattr(type(admin_handler.settings), "is_admin", lambda _self, _uid: True)

    async def _get_ids() -> list[int]:
        return []

    monkeypatch.setattr(
        admin_handler.UserRepository,
        "get_broadcast_telegram_ids",
        staticmethod(_get_ids),
    )

    clear = AsyncMock()
    state = SimpleNamespace(clear=clear)

    answer = AsyncMock()
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=111),
        chat=SimpleNamespace(id=111),
        message_id=10,
        answer=answer,
    )
    bot = SimpleNamespace(copy_message=AsyncMock())

    await admin_handler.admin_broadcast_send(message=message, state=state, bot=bot)

    clear.assert_awaited_once()
    bot.copy_message.assert_not_called()
    answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_broadcast_send_queues_job_and_logs(monkeypatch):
    monkeypatch.setattr(type(admin_handler.settings), "is_admin", lambda _self, _uid: True)

    async def _get_ids() -> list[int]:
        return [1001, 1002, 1003]

    monkeypatch.setattr(
        admin_handler.UserRepository,
        "get_broadcast_telegram_ids",
        staticmethod(_get_ids),
    )

    create_job = AsyncMock(
        return_value=SimpleNamespace(
            id=42,
            created_by_admin_id=777,
            total_users=3,
        )
    )
    monkeypatch.setattr(
        admin_handler.BroadcastJobRepository,
        "create",
        staticmethod(create_job),
    )

    log_create = AsyncMock()
    monkeypatch.setattr(
        admin_handler.AdminActionLogRepository,
        "create",
        staticmethod(log_create),
    )

    clear = AsyncMock()
    state = SimpleNamespace(clear=clear)

    answer = AsyncMock()
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=777),
        chat=SimpleNamespace(id=777),
        message_id=77,
        answer=answer,
    )

    bot = SimpleNamespace(copy_message=AsyncMock())

    await admin_handler.admin_broadcast_send(message=message, state=state, bot=bot)

    bot.copy_message.assert_not_called()
    create_job.assert_awaited_once()
    clear.assert_awaited_once()

    log_create.assert_awaited_once()
    kwargs = log_create.await_args.kwargs
    assert kwargs["action_type"] == "broadcast_queued"
    assert kwargs["target_type"] == "broadcast_job"
    assert kwargs["target_id"] == 42

    answer.assert_awaited_once()
    report = answer.await_args.args[0]
    assert "Job ID: <b>42</b>" in report
    assert "<b>3</b>" in report
